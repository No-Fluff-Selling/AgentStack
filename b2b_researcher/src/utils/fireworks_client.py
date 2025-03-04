"""
Fireworks.ai client utility for accessing DeepSeek R1 (reasoner) via Fireworks.ai API.
Uses the 'accounts/fireworks/models/deepseek-r1' model by default and automatically handles role translation and message processing.
"""
from typing import List, Dict, Any, Optional
import os
import logging
import time
import json
import requests
import re


class FireworksClient:
    """Client for accessing DeepSeek R1 via Fireworks.ai API with automatic role translation and message processing."""
    
    def __init__(self, api_key=None):
        """
        Initialize the Fireworks client.
        
        Args:
            api_key (str, optional): Fireworks API key. Defaults to environment variable.
        """
        self.api_key = api_key or os.environ.get("FIREWORKS_API_KEY")
        if not self.api_key or self.api_key == "<FIREWORKS_API_KEY>":
            raise ValueError("Valid Fireworks API key is required. Set FIREWORKS_API_KEY environment variable, pass api_key parameter, or configure in inputs.yaml.")
        
        self.base_url = "https://api.fireworks.ai/inference/v1/chat/completions"
        logging.info("Initialized Fireworks client")
    
    def _process_messages(self, messages: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """
        Process and validate messages for API compatibility.
        1. Ensures each message has 'role' and 'content' fields
        2. Translates 'developer' role to 'system' role
        3. Defaults to 'user' role if none provided
        4. Ensures content is a string
        
        Args:
            messages (List[Dict[str, Any]]): Raw input messages
            
        Returns:
            List[Dict[str, str]]: Processed messages ready for the API
        """
        processed_messages = []
        
        for msg in messages:
            # Extract role with default of "user"
            role = msg.get("role", "user")
            
            # Translate developer role to system role
            if role == "developer":
                role = "system"
                logging.info("Translated 'developer' role to 'system' role for Fireworks API compatibility")
            
            # Extract content with default of empty string
            content = msg.get("content", "")
            
            # Ensure content is string
            if not isinstance(content, str):
                content = str(content)
            
            # Add processed message
            processed_messages.append({
                "role": role,
                "content": content
            })
        
        return processed_messages
    
    def _clean_response(self, content: str) -> str:
        """
        Clean the response content by removing thinking process.
        
        Args:
            content (str): Raw response content
            
        Returns:
            str: Cleaned response content
        """
        # Remove <think>...</think> blocks
        cleaned_content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL)
        
        # Trim whitespace
        cleaned_content = cleaned_content.strip()
        
        return cleaned_content
    
    def chat_completion(
        self,
        messages: List[Dict[str, Any]],
        model: str = "accounts/fireworks/models/deepseek-r1",
        max_retries: int = 4,
        temperature: float = 0.7,
        max_tokens: Optional[int] = 20480,
        process_messages: bool = True
    ) -> str:
        """
        Get chat completion from Fireworks API with automatic retry for empty responses.
        
        Args:
            messages (List[Dict[str, Any]]): List of message dictionaries.
            model (str, optional): Model to use. Defaults to "accounts/fireworks/models/deepseek-r1".
            max_retries (int, optional): Maximum number of retry attempts. Defaults to 4.
            temperature (float, optional): Sampling temperature. Defaults to 0.7.
            max_tokens (int, optional): Maximum number of tokens to generate. Defaults to 20480.
            process_messages (bool, optional): Whether to automatically process messages. Defaults to True.
            
        Returns:
            str: Response content.
        """
        logging.info(f"Sending request to Fireworks API with model: {model}")
        
        # Process messages if enabled
        if process_messages:
            processed_messages = self._process_messages(messages)
        else:
            processed_messages = messages
        
        # Prepare the parameters
        payload = {
            "model": model,
            "messages": processed_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "top_p": 1,
            "top_k": 40,
            "presence_penalty": 0,
            "frequency_penalty": 0
        }
        
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        attempts = 0
        while attempts < max_retries:
            attempts += 1
            
            if attempts > 1:
                logging.info(f"Retry attempt {attempts} of {max_retries}")
            
            try:
                # Log request details on first attempt
                if attempts == 1:
                    logging.debug(f"Request parameters: {payload}")
                
                # Make the API call
                response = requests.post(
                    self.base_url, 
                    headers=headers, 
                    data=json.dumps(payload)
                )
                response.raise_for_status()  # Raise an exception for HTTP errors
                
                # Parse the response
                response_data = response.json()
                
                # Extract the message content
                content = response_data["choices"][0]["message"]["content"]
                
                # Clean the response to remove thinking process
                content = self._clean_response(content)
                
                # Check if content is empty
                if not content or not content.strip():
                    logging.warning(f"Received empty response (attempt {attempts} of {max_retries})")
                    if attempts < max_retries:
                        # Add a delay before retrying (increasing with each attempt)
                        sleep_time = min(1 * attempts, 5)  # Start with 1s, max 5s
                        logging.info(f"Waiting {sleep_time}s before retry")
                        time.sleep(sleep_time)
                        continue
                
                # If we got a non-empty response, return it
                return content
                
            except Exception as e:
                logging.error(f"Error during attempt {attempts}: {str(e)}")
                if attempts < max_retries:
                    # Add a delay before retrying (increasing with each attempt)
                    sleep_time = min(1 * attempts, 5)  # Start with 1s, max 5s
                    logging.info(f"Waiting {sleep_time}s before retry")
                    time.sleep(sleep_time)
                    continue
                else:
                    # If we've exhausted all retries, raise the exception
                    raise
        
        # If we've exhausted all retries and still have empty responses
        raise Exception(f"Failed to get non-empty response after {max_retries} attempts")
