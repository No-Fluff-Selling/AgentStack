"""
OpenRouter client utility for accessing the Deepseek R1 model using requests.
"""
from typing import List, Dict, Any
import requests
import json
import os
import logging
import time


class OpenRouterClient:
    """Client for accessing OpenRouter API with Deepseek R1 model."""
    
    def __init__(self, api_key=None, site_url=None, site_name=None):
        """
        Initialize the OpenRouter client.
        
        Args:
            api_key (str, optional): OpenRouter API key. Defaults to environment variable.
            site_url (str, optional): Site URL for rankings. Defaults to None.
            site_name (str, optional): Site name for rankings. Defaults to None.
        """
        self.api_key = api_key or os.environ.get("OPENROUTER_API_KEY")
        if not self.api_key or self.api_key == "<OPENROUTER_API_KEY>":
            raise ValueError("Valid OpenRouter API key is required. Set OPENROUTER_API_KEY environment variable, pass api_key parameter, or configure in inputs.yaml.")
        
        self.site_url = site_url
        self.site_name = site_name
        self.base_url = "https://openrouter.ai/api/v1"
        logging.info(f"Initialized OpenRouter client with site: {self.site_name}")
    
    def chat_completion(self, messages: List[Dict[str, str]], model: str = "deepseek/deepseek-r1:free", max_retries: int = 10) -> str:
        """
        Get chat completion from OpenRouter with automatic retry for empty responses.
        
        Args:
            messages (List[Dict[str, str]]): List of message dictionaries.
            model (str, optional): Model to use. Defaults to "deepseek/deepseek-r1:free".
            max_retries (int, optional): Maximum number of retry attempts. Defaults to 10.
            
        Returns:
            str: Response content.
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        if self.site_url:
            headers["HTTP-Referer"] = self.site_url
        if self.site_name:
            headers["X-Title"] = self.site_name
        
        payload = {
            "model": model,
            "messages": [
                {"role": msg.get("role", "user"), "content": msg.get("content", "")}
                for msg in messages
            ]
        }
        
        logging.info(f"Sending request to OpenRouter with model: {model}")
        
        attempts = 0
        while attempts < max_retries:
            attempts += 1
            
            if attempts > 1:
                logging.info(f"Retry attempt {attempts} of {max_retries}")
            
            try:
                logging.info(f"Headers: {headers}") if attempts == 1 else None
                logging.info(f"Payload: {payload}") if attempts == 1 else None
                
                response = requests.post(
                    url=f"{self.base_url}/chat/completions",
                    headers=headers,
                    data=json.dumps(payload)
                )
                
                # Check for successful response
                response.raise_for_status()
                
                # Parse the JSON response
                response_data = response.json()
                
                # Extract the message content
                content = response_data["choices"][0]["message"]["content"]
                
                # Check if content is empty
                if not content.strip():
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

    def handle_error(self, response):
        """
        Handle error responses from the API.
        
        Args:
            response (requests.Response): The response object.
            
        Raises:
            Exception: Appropriate exception based on the error.
        """
        try:
            error_data = response.json()
            error_message = error_data.get("error", {}).get("message", "Unknown error")
            logging.error(f"API Error: {error_message}")
            raise Exception(f"OpenRouter API Error: {error_message}")
        except json.JSONDecodeError:
            logging.error(f"API Error: {response.text}")
            raise Exception(f"OpenRouter API Error: {response.status_code} - {response.text}")