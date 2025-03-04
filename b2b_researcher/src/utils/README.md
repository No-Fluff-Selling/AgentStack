# OpenRouter Integration

This directory contains utilities for integrating with external LLM providers, including OpenRouter for accessing models like Deepseek R1.

## OpenRouter Client

The `openrouter_client.py` module provides a client for accessing the OpenRouter API, which allows using various LLM models including Deepseek R1.

### Configuration

To use the OpenRouter client, you need to configure your API key in one of the following ways:

1. In the `src/config/inputs.yaml` file:
   ```yaml
   llm:
     openrouter:
       api_key: "your-api-key-here"
       site_url: "https://b2bresearcher.com"
       site_name: "B2B Researcher"
   ```

2. As an environment variable:
   ```bash
   export OPENROUTER_API_KEY="your-api-key-here"
   ```

3. Directly in code when initializing the client:
   ```python
   from src.utils.openrouter_client import OpenRouterClient
   
   client = OpenRouterClient(
       api_key="your-api-key-here",
       site_url="https://your-site.com",
       site_name="Your Site Name"
   )
   ```

### Usage

The OpenRouter client is used in the `execute_rag_process` function to generate reports with the Deepseek R1 model when specified.

To use the Deepseek R1 model for report generation, the `model` parameter is set to "deepseek-r1" in the following functions:
- `generate_user_company_report`
- `generate_target_company_report`

If the OpenRouter API key is not configured or there's an error with the OpenRouter API, the system will fall back to using the default model (o3-mini) via the standard `track_chat_completion` method.
