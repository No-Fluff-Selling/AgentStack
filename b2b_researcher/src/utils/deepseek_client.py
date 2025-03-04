"""
DeepSeek R1 client utility for accessing DeepSeek's API using the OpenAI client library.
Uses the 'deepseek-reasoner' model by default and automatically handles role translation and message processing.
"""
from typing import List, Dict, Any, Optional
import os
import logging
import time
from openai import OpenAI


class DeepseekClient:
    """Client for accessing DeepSeek R1 API with automatic role translation and message processing."""
    
    def __init__(self, api_key=None):
        """
        Initialize the Deepseek client.
        
        Args:
            api_key (str, optional): Deepseek API key. Defaults to environment variable.
        """
        self.api_key = api_key or os.environ.get("DEEPSEEK_API_KEY")
        if not self.api_key or self.api_key == "<DEEPSEEK_API_KEY>":
            raise ValueError("Valid Deepseek API key is required. Set DEEPSEEK_API_KEY environment variable, pass api_key parameter, or configure in inputs.yaml.")
        
        self.client = OpenAI(
            api_key=self.api_key,
            base_url="https://api.deepseek.com",
            timeout=90.0  # Add 90-second timeout
        )
        logging.info("Initialized Deepseek client")
    
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
                logging.info("Translated 'developer' role to 'system' role for Deepseek API compatibility")
            
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
    
    def chat_completion(
        self,
        messages: List[Dict[str, Any]],
        model: str = "deepseek-reasoner",
        max_retries: int = 4,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        process_messages: bool = True
    ) -> str:
        """
        Get chat completion from Deepseek API with automatic retry for empty responses.
        
        Args:
            messages (List[Dict[str, Any]]): List of message dictionaries.
            model (str, optional): Model to use. Defaults to "deepseek-chat".
            max_retries (int, optional): Maximum number of retry attempts. Defaults to 10.
            temperature (float, optional): Sampling temperature. Defaults to 0.7.
            max_tokens (int, optional): Maximum number of tokens to generate. Defaults to None.
            process_messages (bool, optional): Whether to automatically process messages. Defaults to True.
            
        Returns:
            str: Response content.
        """
        logging.info(f"Sending request to Deepseek API with model: {model}")
        
        # Process messages if enabled
        if process_messages:
            processed_messages = self._process_messages(messages)
        else:
            processed_messages = messages
        
        # Prepare the parameters
        params = {
            "model": model,
            "messages": processed_messages,
            "temperature": temperature,
            "stream": False
        }
        
        # Add max_tokens if provided
        if max_tokens is not None:
            params["max_tokens"] = max_tokens
        
        attempts = 0
        while attempts < max_retries:
            attempts += 1
            
            if attempts > 1:
                logging.info(f"Retry attempt {attempts} of {max_retries}")
            
            try:
                # Log request details on first attempt
                if attempts == 1:
                    logging.debug(f"Request parameters: {params}")
                
                # Make the API call
                response = self.client.chat.completions.create(**params)
                
                # Extract the message content
                content = response.choices[0].message.content
                
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