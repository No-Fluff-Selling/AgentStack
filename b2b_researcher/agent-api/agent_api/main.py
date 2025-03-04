import json
import asyncio
import aiohttp
import logging
import os
import sys
import traceback
from typing import Dict
from datetime import datetime
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Body
from pydantic import BaseModel
from .models import AnalysisStep, AgentExecutionRequest, AgentExecutionResponse
from .data import ANALYSIS_STEPS, EXAMPLE_REPORT

# Add the project root directory to the Python path to allow importing from src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
# Import the B2bresearcherGraph
from src.graph import B2bresearcherGraph

app = FastAPI()
# Enhanced logging configuration
logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("app.log")
    ]
)
logger = logging.getLogger(__name__)

REMIX_HOST = os.getenv("REMIX_HOST", "localhost:3000")


class Execution(BaseModel):
    active: bool
    subscribers: set[WebSocket]
    steps: list[AnalysisStep]
    start_time: datetime
    last_update_time: datetime

    class Config:
        arbitrary_types_allowed = True


class AgentExecutionManager:
    def __init__(self):
        # Store all execution data in a single dict with structure:
        # { submission_id: { 'active': bool, 'subscribers': set[WebSocket], 'steps': list[AnalysisStep] } }
        self.executions: Dict[str, Execution] = {}
        logger.info("AgentExecutionManager initialized")

    def start_execution(self, submission_id: str) -> bool:
        """Start a new agent execution if it doesn't exist"""
        if submission_id in self.executions:
            logger.warning(f"[{submission_id}] Execution already exists with {len(self.executions[submission_id].subscribers)} subscribers")
            return False
        
        now = datetime.now()
        logger.info(f"[{submission_id}] Starting new execution at {now.isoformat()}")
        self.executions[submission_id] = Execution(
            active=True, 
            subscribers=set(), 
            steps=[],
            start_time=now,
            last_update_time=now
        )
        return True

    async def subscribe_client(self, websocket: WebSocket, submission_id: str) -> bool:
        """Subscribe a client to an existing execution"""
        client_id = id(websocket)
        
        if submission_id not in self.executions:
            logger.warning(f"[{submission_id}] No execution found for client {client_id}")
            return False

        try:
            logger.info(f"[{submission_id}] Accepting WebSocket connection for client {client_id}")
            await websocket.accept()
            
            self.executions[submission_id].subscribers.add(websocket)
            subscription_count = len(self.executions[submission_id].subscribers)
            logger.info(f"[{submission_id}] Client {client_id} subscribed successfully. Total subscribers: {subscription_count}")

            # Log connection details
            connection_info = {
                "client_id": client_id,
                "submission_id": submission_id,
                "subscription_time": datetime.now().isoformat(),
                "execution_age": (datetime.now() - self.executions[submission_id].start_time).total_seconds(),
                "step_count": len(self.executions[submission_id].steps)
            }
            logger.info(f"WebSocket connection details: {json.dumps(connection_info)}")

            # Send historical steps immediately to the new subscriber
            logger.info(f"[{submission_id}] Broadcasting {len(self.executions[submission_id].steps)} historical steps to client {client_id}")
            await self.broadcast_state(submission_id, specific_client=websocket)
            return True
            
        except Exception as e:
            logger.error(f"[{submission_id}] Error subscribing client {client_id}: {str(e)}")
            logger.error(traceback.format_exc())
            return False

    def add_step(self, submission_id: str, step: AnalysisStep):
        """Add a step to the execution history"""
        if submission_id in self.executions:
            now = datetime.now()
            time_since_start = (now - self.executions[submission_id].start_time).total_seconds()
            time_since_update = (now - self.executions[submission_id].last_update_time).total_seconds()
            
            logger.info(f"[{submission_id}] Adding step {step.idx}/{step.totalSteps} ({time_since_start:.2f}s since start, {time_since_update:.2f}s since last update)")
            
            self.executions[submission_id].steps.append(step)
            self.executions[submission_id].last_update_time = now
            
            # Log step contents for debugging
            step_dict = step.model_dump()
            logger.info(f"[{submission_id}] Step content: {json.dumps(step_dict, indent=2)}")
            
            # Trigger message broadcast after adding new step
            subscribers_count = len(self.executions[submission_id].subscribers)
            logger.info(f"[{submission_id}] Broadcasting new step to {subscribers_count} subscribers")
            asyncio.create_task(self.broadcast_state(submission_id))

    async def broadcast_state(self, submission_id: str, specific_client: WebSocket = None):
        """Broadcast current execution state to all subscribed clients to a particular execution"""
        if submission_id in self.executions:
            execution = self.executions[submission_id]
            
            # Convert all steps to dict format and send as a list
            steps_data = [step.model_dump() for step in execution.steps]
            message = json.dumps(steps_data)
            
            target_clients = [specific_client] if specific_client else execution.subscribers
            client_count = len(target_clients)
            
            logger.info(f"[{submission_id}] Broadcasting {len(steps_data)} steps to {client_count} clients")

            disconnected = set()
            success_count = 0
            
            for websocket in target_clients:
                client_id = id(websocket)
                try:
                    await websocket.send_text(message)
                    success_count += 1
                    logger.info(f"[{submission_id}] Successfully sent update to client {client_id}")
                except WebSocketDisconnect:
                    logger.warning(f"[{submission_id}] Client {client_id} disconnected during broadcast")
                    disconnected.add(websocket)
                except Exception as e:
                    logger.error(f"[{submission_id}] Error sending to client {client_id}: {str(e)}")
                    logger.error(traceback.format_exc())
                    disconnected.add(websocket)

            # Clean up any disconnected websockets
            for websocket in disconnected:
                self.unsubscribe_client(websocket, submission_id)
                
            logger.info(f"[{submission_id}] Broadcast summary: {success_count} successful, {len(disconnected)} failed")

    def unsubscribe_client(self, websocket: WebSocket, submission_id: str):
        """Unsubscribe a client"""
        client_id = id(websocket)
        if submission_id in self.executions:
            was_subscribed = websocket in self.executions[submission_id].subscribers
            self.executions[submission_id].subscribers.discard(websocket)
            remaining = len(self.executions[submission_id].subscribers)
            
            if was_subscribed:
                logger.info(f"[{submission_id}] Client {client_id} unsubscribed. {remaining} subscribers remaining")
            else:
                logger.warning(f"[{submission_id}] Attempted to unsubscribe client {client_id} that wasn't subscribed")

    def finish_execution(self, submission_id: str):
        """Clean up execution resources"""
        if submission_id in self.executions:
            execution = self.executions[submission_id]
            duration = (datetime.now() - execution.start_time).total_seconds()
            subscriber_count = len(execution.subscribers)
            step_count = len(execution.steps)
            
            logger.info(f"[{submission_id}] Finishing execution after {duration:.2f}s with {step_count} steps completed")
            logger.info(f"[{submission_id}] Closing connections for {subscriber_count} subscribers")
            
            # Close any remaining connections
            for websocket in list(execution.subscribers):
                try:
                    asyncio.create_task(websocket.close(code=1000, reason="Execution completed"))
                except Exception as e:
                    logger.warning(f"[{submission_id}] Error closing websocket: {str(e)}")
            
            del self.executions[submission_id]
            logger.info(f"[{submission_id}] Execution resources cleaned up successfully")
            
            # Log current state of manager
            active_executions = len(self.executions)
            logger.info(f"Manager status: {active_executions} active executions")


manager = AgentExecutionManager()


@app.post("/submit")
async def start_agent_execution(
    request: AgentExecutionRequest,
) -> AgentExecutionResponse:
    """Trigger a new agent execution"""
    logger.info(f"Received submission request for {request.submissionId}")
    logger.info(f"Request details: company_url={request.companyUrl}, target_url={request.targetUrl}")
    
    if not manager.start_execution(request.submissionId):
        logger.warning(f"[{request.submissionId}] Execution already exists - rejecting request")
        raise HTTPException(
            status_code=400, detail="Execution already exists for this submission ID"
        )

    logger.info(f"[{request.submissionId}] Starting agent execution in background task")
    # Start the agent execution in the background
    asyncio.create_task(langgraph_agent(request.submissionId, request.companyUrl, request.targetUrl))

    response = AgentExecutionResponse(
        submissionId=request.submissionId, status="processing", startedAt=datetime.now()
    )
    logger.info(f"[{request.submissionId}] Submission accepted, returning response")
    return response


@app.get("/health")
async def health_check():
    active_executions = len(manager.executions)
    logger.info(f"Health check requested. {active_executions} active executions")
    
    # Include more detailed status in health check
    execution_statuses = {}
    for submission_id, execution in manager.executions.items():
        execution_statuses[submission_id] = {
            "active": execution.active,
            "subscribers": len(execution.subscribers),
            "steps": len(execution.steps),
            "runtime": (datetime.now() - execution.start_time).total_seconds()
        }
    
    return {
        "status": "healthy", 
        "timestamp": datetime.utcnow().isoformat(),
        "activeExecutions": active_executions,
        "executionDetails": execution_statuses
    }


@app.websocket("/ws/{submission_id}")
async def websocket_endpoint(websocket: WebSocket, submission_id: str):
    """Subscribe to an existing agent execution"""
    client_id = id(websocket)
    logger.info(f"[{submission_id}] New WebSocket connection request from client {client_id}")
    
    if not await manager.subscribe_client(websocket, submission_id):
        logger.warning(f"[{submission_id}] No active execution found for client {client_id} - closing connection")
        try:
            await websocket.close(
                code=4000, reason="No active execution found for this submission ID"
            )
        except Exception as e:
            logger.error(f"[{submission_id}] Error closing websocket: {str(e)}")
        return

    try:
        # Keep the connection alive until disconnect
        logger.info(f"[{submission_id}] Client {client_id} connected successfully, entering message loop")
        while True:
            message = await websocket.receive_text()
            logger.info(f"[{submission_id}] Received message from client {client_id}: {message[:100]}...")
    except WebSocketDisconnect as e:
        logger.info(f"[{submission_id}] WebSocket disconnect from client {client_id}, code: {e.code}")
        manager.unsubscribe_client(websocket, submission_id)
    except Exception as e:
        logger.error(f"[{submission_id}] WebSocket error from client {client_id}: {str(e)}")
        logger.error(traceback.format_exc())
        manager.unsubscribe_client(websocket, submission_id)


async def langgraph_agent(submission_id: str, company_url: str = "", target_url: str = ""):
    """Execute the agent and send updates to connected clients"""
    logger.info(f"[{submission_id}] langgraph_agent task started")
    logger.info(f"[{submission_id}] Parameters: company_url={company_url}, target_url={target_url}")
    
    try:
        # Use dummy data if no URLs are provided (for backward compatibility)
        if not company_url or not target_url:
            logger.warning(f"[{submission_id}] No URLs provided - using dummy data for backward compatibility")
            for i, step in enumerate(ANALYSIS_STEPS):
                logger.info(f"[{submission_id}] Processing dummy step {i+1}/{len(ANALYSIS_STEPS)}")
                
                current_step = AnalysisStep(
                    idx=i,
                    message=step["message"],
                    details=step["details"],
                    output=step["output"],
                    totalSteps=len(ANALYSIS_STEPS),
                )
                # Add step to manager which will trigger broadcasting to all subscribers
                manager.add_step(submission_id, current_step)
                
                # Skip await in last iteration
                if i != len(ANALYSIS_STEPS) - 1:
                    delay_ms = 1 * step["delay"] / 1000
                    logger.info(f"[{submission_id}] Waiting {delay_ms}s before next step")
                    await asyncio.sleep(delay_ms)
                    
            # Send dummy report data
            logger.info(f"[{submission_id}] All dummy steps completed, preparing to send report")
            report_data = EXAMPLE_REPORT
        else:
            # Initialize and run B2bresearcherGraph
            logger.info(f"[{submission_id}] Initializing B2bresearcherGraph with user_url={company_url} and target_url={target_url}")
            try:
                graph = B2bresearcherGraph(enable_db_save=True)
                logger.info(f"[{submission_id}] B2bresearcherGraph initialized successfully")
            except Exception as e:
                logger.error(f"[{submission_id}] Failed to initialize B2bresearcherGraph: {str(e)}")
                logger.error(traceback.format_exc())
                raise
            
            # Prepare input for the graph
            inputs = {
                "user_url": company_url,
                "target_url": target_url,
                "submission_id": submission_id,
            }
            logger.info(f"[{submission_id}] Prepared graph inputs: {json.dumps(inputs)}")
            
            # Define step mapping for frontend display
            step_mapping = {
                0: {
                    "message": "Initializing AI analysis engine",
                    "details": "Setting up neural networks and loading analysis models",
                    "output": "Models loaded successfully. Initializing analysis framework and preparing web intelligence modules."
                },
                1: {
                    "message": "Crawling your company website",
                    "details": f"Extracting key information about {graph.get_company_name_from_url(company_url)}",
                    "output": "Analyzing website structure and key capabilities."
                },
                2: {
                    "message": "Processing your company data",
                    "details": "Analyzing your services and expertise",
                    "output": "Extracting core capabilities and value propositions."
                },
                3: {
                    "message": "Generating your company profile",
                    "details": "Creating a comprehensive analysis of your services",
                    "output": "Profile generated with key strengths and capabilities."
                },
                4: {
                    "message": "Crawling target company website",
                    "details": f"Gathering public information about {graph.get_company_name_from_url(target_url)}",
                    "output": "Website structure analyzed and core pages identified."
                },
                5: {
                    "message": "Analyzing target company data",
                    "details": "Extracting business model and operations",
                    "output": "Key business areas and company structure identified."
                },
                6: {
                    "message": "Researching target's news and market position",
                    "details": "Gathering recent company news and updates",
                    "output": "Collected latest news, market information, and business developments."
                },
                7: {
                    "message": "Analyzing target's job postings",
                    "details": "Identifying hiring patterns and growth areas",
                    "output": "Job listings analyzed for business priorities and expansion areas."
                },
                8: {
                    "message": "Identifying industry trends and market context",
                    "details": "Researching relevant industry developments",
                    "output": "Industry trends and market dynamics analyzed."
                },
                9: {
                    "message": "Generating comprehensive sales intelligence report",
                    "details": "Combining all analysis into actionable insights",
                    "output": "Final report generated with strategic recommendations."
                }
            }
            
            # Create a mapping between state keys/operations and UI steps
            # This maps graph progress to UI steps more accurately
            state_to_step_mapping = {
                "branches.user.sitemap_urls": 1,  # User website crawling
                "branches.user.page_contents": 2,  # Processing user company data
                "branches.user.report": 3,         # User company profile generation
                "branches.target.sitemap_urls": 4, # Target website crawling
                "branches.target.page_contents": 5, # Target data analysis
                "branches.target.news_data": 6,    # Target news research
                "branches.target.job_listings": 7, # Job postings analysis
                "branches.target.macro_trends_data": 8, # Industry trends
                "branches.target.report": 9,       # Final report generation
            }
            
            # Execute the graph
            total_steps = 10  # Fixed total of 10 steps for UI consistency
            current_step_idx = 0
            
            logger.info(f"[{submission_id}] Starting graph execution with {total_steps} total steps")
            
            # Send the first step (step 0) before running the generator
            first_step = AnalysisStep(
                idx=current_step_idx,
                message=step_mapping[current_step_idx]["message"],
                details=step_mapping[current_step_idx]["details"],
                output=step_mapping[current_step_idx]["output"],
                totalSteps=total_steps,
            )
            manager.add_step(submission_id, first_step)
            current_step_idx += 1
            logger.info(f"[{submission_id}] First step (step 0) sent, waiting before starting graph execution")
            await asyncio.sleep(1)  # Brief delay before starting
            
            # Send step 1 after brief delay to ensure UI doesn't get stuck at step 0
            logger.info(f"[{submission_id}] Sending UI step 1 to start progress")
            step_one = AnalysisStep(
                idx=current_step_idx,
                message=step_mapping[current_step_idx]["message"],
                details=step_mapping[current_step_idx]["details"],
                output=step_mapping[current_step_idx]["output"],
                totalSteps=total_steps,
            )
            manager.add_step(submission_id, step_one)
            current_step_idx += 1
            last_processed_step = 1  # Mark step 1 as processed
            await asyncio.sleep(0.5)
            
            # Define a step tracking mapping from node names to UI steps
            node_to_step_mapping = {
                "user_sitemap": 2,
                "user_scraping": 3,
                "user_report": 4,
                "target_sitemap": 5,
                "target_scraping": 6,
                "target_news": 7,
                "target_job_listings": 8,
                "target_macro_trends": 9,
                "target_report": 9,
                "overview": 9,
                "positions": 9,
                "news_section": 9,
                "macro_trends": 9,
                "combine_sections": 9,
                "end": 10
            }
            
            # Define the on_step callback to update UI based on node status
            async def on_node_progress(state, node_name, description):
                nonlocal current_step_idx, last_processed_step
                
                # Log node progress
                logger.info(f"[{submission_id}] Node progress: {node_name} - {description}")
                
                # Map node name to UI step
                if node_name in node_to_step_mapping:
                    next_step = node_to_step_mapping[node_name]
                    
                    # Only advance to next step if we haven't processed it yet
                    if next_step > last_processed_step:
                        logger.info(f"[{submission_id}] Advancing UI from step {last_processed_step} to {next_step} based on node {node_name}")
                        
                        # Send all steps between the last processed step and the next step
                        while current_step_idx < next_step and current_step_idx < total_steps:
                            logger.info(f"[{submission_id}] Sending UI step {current_step_idx}/{total_steps}")
                            
                            current_step = AnalysisStep(
                                idx=current_step_idx,
                                message=step_mapping[current_step_idx]["message"],
                                details=step_mapping[current_step_idx]["details"],
                                output=step_mapping[current_step_idx]["output"],
                                totalSteps=total_steps,
                            )
                            manager.add_step(submission_id, current_step)
                            current_step_idx += 1
                            
                            # Brief delay between steps for UI feedback
                            await asyncio.sleep(0.5)
                        
                        last_processed_step = next_step
                    else:
                        logger.info(f"[{submission_id}] Already at or beyond step {next_step}, currently at step {last_processed_step}")
                else:
                    logger.warning(f"[{submission_id}] Unknown node name: {node_name}")
            
            logger.info(f"[{submission_id}] Beginning graph execution with progress tracking")
            step_start_time = datetime.now()
            
            # Run the graph with progress tracking
            try:
                # Create a wrapper for the on_node_progress callback that doesn't require async
                def on_step_wrapper(state, node_name, description):
                    asyncio.create_task(on_node_progress(state, node_name, description))
                
                # Use the built-in progress tracking instead of manual state inspection
                final_state = graph.run_with_progress_tracking(inputs, on_step_wrapper)
                
                # Ensure we reach the final step
                while current_step_idx < total_steps:
                    logger.info(f"[{submission_id}] Sending final UI step {current_step_idx}/{total_steps}")
                    current_step = AnalysisStep(
                        idx=current_step_idx,
                        message=step_mapping[current_step_idx]["message"],
                        details=step_mapping[current_step_idx]["details"],
                        output=step_mapping[current_step_idx]["output"],
                        totalSteps=total_steps,
                    )
                    manager.add_step(submission_id, current_step)
                    current_step_idx += 1
                    await asyncio.sleep(0.5)
                
                logger.info(f"[{submission_id}] Graph execution completed")
                
            except Exception as e:
                error_msg = f"Error during graph execution: {str(e)}"
                logger.error(f"[{submission_id}] {error_msg}")
                logger.error(traceback.format_exc())
                
                # Create an error step to notify the user
                error_step = AnalysisStep(
                    idx=current_step_idx,
                    message="Execution Error",
                    details=f"Error during analysis: {str(e)}",
                    output=f"Stack trace: {traceback.format_exc()[:500]}...",
                    totalSteps=total_steps,
                )
                manager.add_step(submission_id, error_step)
            
            # Extract the report from the final state
            if graph.error:
                logger.error(f"[{submission_id}] Error occurred during graph execution: {graph.error}")
                # Create an error step
                error_step = AnalysisStep(
                    idx=9,  # Use the last step index
                    message="Error occurred",
                    details=f"An error occurred during analysis: {graph.error}",
                    output="Please try again or contact support if the issue persists.",
                    totalSteps=10,
                )
                manager.add_step(submission_id, error_step)
                report_data = f"# Error in Analysis\n\nAn error occurred during analysis: {graph.error}"
            else:
                # Get report from the final state
                logger.info(f"[{submission_id}] Extracting report from final state")
                final_state = graph.current_state
                
                # Log the structure of the final state
                if final_state:
                    state_structure = {k: type(v).__name__ for k, v in final_state.items()}
                    logger.info(f"[{submission_id}] Final state structure: {json.dumps(state_structure)}")
                else:
                    logger.warning(f"[{submission_id}] Empty final state")
                
                if final_state and "branches" in final_state:
                    # Extract report from state
                    if "target" in final_state["branches"] and "report" in final_state["branches"]["target"]:
                        logger.info(f"[{submission_id}] Report found in final state")
                        report_data = final_state["branches"]["target"]["report"]
                        # Log report size
                        report_size = len(report_data)
                        logger.info(f"[{submission_id}] Report size: {report_size} characters")
                    else:
                        logger.warning(f"[{submission_id}] No target report found in final state")
                        report_data = "# Report Generation Incomplete\n\nThe system couldn't generate a complete report. Please try again."
                else:
                    logger.warning(f"[{submission_id}] Invalid final state structure")
                    report_data = "# Report Generation Failed\n\nThe system encountered an issue while generating the report. Please try again."

        # Send the final report to the reports endpoint
        logger.info(f"[{submission_id}] Sending final report to reports endpoint")
        async with aiohttp.ClientSession() as session:
            protocol = "https" if bool(os.getenv("FLY_APP_NAME")) else "http"
            report_endpoint = f"{protocol}://{REMIX_HOST}/reports/{submission_id}"
            
            logger.info(f"[{submission_id}] Sending report to: {report_endpoint}")
            
            try:
                async with session.post(
                    report_endpoint,
                    data=json.dumps({"result": report_data}),
                    headers={"Content-Type": "application/json"},
                ) as response:
                    status = response.status
                    logger.info(f"[{submission_id}] Report submission response status: {status}")
                    
                    if status != 200:
                        response_text = await response.text()
                        logger.error(f"[{submission_id}] Failed to send report. Status: {status}, Response: {response_text}")
                    else:
                        logger.info(f"[{submission_id}] Report successfully submitted")
            except Exception as e:
                logger.error(f"[{submission_id}] Error sending report to endpoint: {str(e)}")
                logger.error(traceback.format_exc())
                
        logger.info(f"[{submission_id}] langgraph_agent task completed successfully")
                
    except Exception as e:
        logger.error(f"[{submission_id}] Error in langgraph_agent: {str(e)}")
        logger.error(traceback.format_exc())
        
        # Try to notify the client about the error
        try:
            error_step = AnalysisStep(
                idx=9,  # Use the last step index
                message="Error occurred",
                details=f"An error occurred during analysis: {str(e)}",
                output="Please try again or contact support if the issue persists.",
                totalSteps=10,
            )
            manager.add_step(submission_id, error_step)
            logger.info(f"[{submission_id}] Error notification step added")
        except Exception as inner_e:
            logger.error(f"[{submission_id}] Error while sending error notification: {str(inner_e)}")
            logger.error(traceback.format_exc())
    finally:
        logger.info(f"[{submission_id}] Cleaning up execution resources")
        manager.finish_execution(submission_id)