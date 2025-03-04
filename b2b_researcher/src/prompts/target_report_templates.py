"""Target company analysis report templates and prompts."""

# Required sections for report validation
# These sections are used in the validate_target_report_content method to ensure that
# generated reports contain all necessary components for effective sales intelligence.
# Each section serves a specific purpose in the sales process:
# - Open Positions: Provides insight into current hiring needs
# - Current Events: Highlights recent developments and news
# - Macro Trends: Identifies key industry trends and statistics
# - Company Info: Offers detailed information about the company's business model and offerings
TARGET_REQUIRED_SECTIONS = [
    "1. Open Positions",
    "2. Current Events (Last 12 Months)",
    "3. Macro Trends",
    "4. {company_name} Info"
]

# Key focus areas for adaptive query generation prompt
# These focus areas are used in the generate_adaptive_queries method in graph.py to generate
# targeted questions about potential client companies. The method uses these areas to create
# a prompt for an LLM that generates specific questions to gather sales-relevant information.
# Each focus area represents a critical aspect of understanding a potential client for B2B sales:
# 1. Current job openings and hiring trends - To identify timing and urgency
# 2. Recent news and developments - To understand recent changes and initiatives
# 3. Industry macro trends and statistics - To understand market context and challenges
# 4. Core business model and offerings - To understand the company's products and services
# 5. Target market and customer segments - To understand the company's target customers
# 6. Unique value proposition and differentiation - To understand the company's competitive advantage
TARGET_FOCUS_AREAS = [
    "Current job openings and hiring trends",
    "Recent news and developments (last 12 months)",
    "Industry macro trends and statistics",
    "Core business model and offerings",
    "Target market and customer segments",
    "Unique value proposition and differentiation"
]

# Fallback queries for target company research
# These queries are used as a backup in the generate_fallback_queries method when
# the adaptive query generation fails. They are designed to cover essential aspects
# of understanding a potential client company for B2B sales purposes:
# - Current job openings and hiring trends
# - Recent news and developments
# - Industry macro trends and statistics
# - Company products and services
# - Target market and customer segments
# - Unique value proposition and differentiation
TARGET_FALLBACK_QUERIES = [
    "What are the current job openings at the company?",
    "What major news or developments have occurred in the last 12 months?",
    "What are the key macro trends affecting their industry?",
    "What shocking or notable statistics exist about their industry?",
    "What products or services does the company offer?",
    "Who is their target market?",
    "What is their unique selling proposition?",
    "How do they differentiate from competitors?"
]

# Report template for target company analysis
# This template is used in the generate_target_company_report method to create
# comprehensive sales intelligence reports. It provides a structured format that:
# 1. Ensures consistent report organization
# 2. Emphasizes critical sales intelligence components
# 3. Maintains high standards for evidence and citations
# 4. Focuses on actionable insights for sales teams
# The template includes specific instructions for:
# - Required sections and their content
# - Citation requirements and formatting
# - Evidence standards and verification
TARGET_REPORT_TEMPLATE = """Use the "Available News Data", "Available Webpage Data", "Available Job Data", and "Available Macro Data" (below) to fill in the template, creating a comprehensive sales intelligence report about {company_name}, with citations. Write your reponse in properly-formatted markdown.
Key Requirements:
1. For in-text citations: use IEEE citation style with square brackets (e.g. "[1]").
2. Use the original citation numbers provided in the source data. Do not attempt to renumber citations.
3. Format output in markdown.
4. Do not write a preface to the report; begin your output immediately with the first line of the template ("# {company_name} Sales Intelligence Report")

<start of template> 
# {company_name} Sales Intelligence Report

## {company_name} Company Overview

### What does {company_name} do/sell/offer?
[Provide a clear, concise narrative of the company's products/services and business model, with citations. Aim for 3-5 sentences. Use citations!]

### Who is {company_name}'s target market?
[Describe the company's target customers and market segments, with citations. Aim for 3-5 sentences. Use citations!]

### What is {company_name}'s unique selling proposition?
[Explain what differentiates {company_name} from competitors, with citations. Aim for 3-5 sentences. Use citations!]

## Open Positions at {company_name}
[List the job title of each job listing found for {company_name} in a bullet-pointed list, with citations. Then, in a separate paragraph, describe what can be inferred about {company_name} based on the job listings. Pay special attention to any mention of tools, technologies or methodologies associated with the job and, if appropriate, mention the exact tools, technologies, or methodolgies by name. If no listings found, output "No open positions found in a quick scan of {company_name}'s website. Want more in-depth results? Contact us." (Make the "Contact us" hyperlink clickable to https://www.nofluffselling.com/contact).]
<br>"Note: Job listings are sourced solely from {company_name}'s website."
<br>"Want more in-depth results? <a href="https://www.nofluffselling.com/contact" target="_blank">Contact us</a>"

## {company_name} News (Last 12 Months)
[Using the "Available News Data" (provided below) and your own knowledge, summarize 3-7 major news developments about {company_name} from the last 12 months that are relevant to the services and products offered by {user_company_name} which is described in the "Available User Company Report Data" included below. Cite real news data sources. For each event, summarize the event using cited, factual evidence. Then, in a second paragraph, summarize what the event infers about {company_name}. Then, in a third paragraph, summarize what the event infers about the potential value of {user_company_name}'s offerings to {company_name}. Don't use bullet-points, but do separate each event with a descriptive heading. If no news found, output "No current events found".]
[Use this format for each event:
### Descriptive News Development Title
<br>3-5 sentences news development summary, with citations
<br><b>{company_name} Impact Inference:</b> 3-5 sentences summary of what can be inferred about {company_name}.
<br><b>{user_company_name} Inference:</b> 3-5 sentences summary of what can be inferred about {company_name}'s potential use for {user_company_name}'s product/service offerings.]

## Industry Macro Trends
[Using the "Available Macro Data" (provided below), and your own knowledge, synthesize up to 5 broad market (macro) trends for the industry/industries that {company_name} operates in, highlighting key events, policy changes, technological innovations, and any notable shifts in consumer behavior. Combine information from multiple data sources to deduce each market trend you synthesize and use (multiple) citations to substantiate every trend. Cite real data sources only! For each trend, detail the trend and then, in a second paragraph, summarize how the trend might impact companies in the industry. If the impact is factual, cite the source. If no trends are found, output "No macro trends found".]
[Use this format for each trend:
### Descriptive Macro Trend Title
<br>3-5 sentences trend description, with multiple citations
<br><b>Impact:</b> 3-5 sentence description of the trend's impact on companies in the industry.]

## Shocking Statistics
[If sufficient data exists within the available data sources, list up to 3 compelling statistics about the industry {company_name} operates in, with citations, that could help build rapport. These compelling/shocking industy statistics should be industry-wide, as opposed to statistics specifically about {company_name}. Don't use bullet-points, but do separate each statistic with a descriptive heading. If no statistics are found, omit this section.]

Include a section (with no heading) noting: "Note: This analysis is based on publicly available information from {company_name}'s online presence, news coverage, and market research.<br>Want more in-depth information about this industry and companies operating in it? Contact us at <href="mailto:sales@nofluffselling.com" target="_blank">sales@nofluffselling.com</href>."

## Citations
[Format the list of citations so that each ciation is on a new line and only the number, brackets included, is hyperlinked to the corresponding source URL, and is followed by the page title and then the URL (e.g. <a href="https://webflow.bigeye.com" target="_blank">[1]</a>. [Bigeye data observability] - (https://webflow.bigeye.com)]
{citations}

<end of template> 

**Available News Data:**
{news_context}

**Available Webpage Data:**
{webpage_context}

**Available Job Data:**
{job_context}
{hiring_info_context}

**Available Macro Data:**
{macro_context}

**Available User Company Report Data:**
{user_report}
"""

# Verification prompt for target company analysis
# This prompt is used in the verify_target_company_analysis method to ensure that
# the generated report meets the required standards for evidence and citations.
# It checks for:
# - Proper citation formatting and sequencing
# - Evidence support for all claims
# - Completeness of critical information categories
TARGET_VERIFICATION_PROMPT = """Verify the sales intelligence report using this checklist:
1. Check structural requirements
2. Validate content formatting
3. Verify citation integrity

[STRUCTURE]
✅ Main heading: {company_name} Sales Intelligence Report
✅ Company Overview with 3 subsections:
   - What does {company_name} do/sell/offer?
   - Who is their target market?
   - Unique selling proposition
✅ Open Positions section with bullet points
✅ News section with 3-7 developments
✅ Macro Trends section with impact analysis
✅ Shocking Statistics (if applicable)
✅ Citations section

[CONTENT]
✅ Company Overview subsections have 3-5 cited sentences
✅ Open Positions includes inference paragraph
✅ Each news event has:
   - Descriptive title
   - Factual summary
   - {company_name} impact inference
   - {user_company_name} value inference
✅ Macro trends combine multiple data sources
✅ Statistics are industry-wide (when present)
✅ Professional business tone maintained
✅ Strategic use of bold to highlight key points
✅ No uncited claims

[CITATIONS]
✅ Citations section content matches the template
✅ Each citation is on a new line

Context:
{{}}

Respond using this format:
PASS: All requirements met
or
FAIL: Missing [CATEGORY] - [REQUIREMENT] (Found/Not Found)
..."""


# Company Overview section template
COMPANY_OVERVIEW_TEMPLATE = """Use the "Available Webpage Data" (below) to fill in the template, creating a comprehensive sales intelligence report about {company_name}, with citations.
Key Requirements:
1. For in-text citations: use IEEE citation style with square brackets (e.g. "[1]").
2. Use the original citation numbers provided in the source data. Do not attempt to renumber citations.
3. Format output in markdown.
4. Do not write a preface to the report; begin your output immediately with the first line of the template.

<start of template> 
## {company_name} Company Overview

### What does {company_name} do/sell/offer?
[Provide a clear, concise narrative of the company's products/services and business model, with citations. Aim for 3-5 sentences. Use citations!]

### Who is {company_name}'s target market?
[Describe the company's target customers and market segments, with citations. Aim for 3-5 sentences. Use citations!]

### What is {company_name}'s unique selling proposition?
[Explain what differentiates {company_name} from competitors, with citations. Aim for 3-5 sentences. Use citations!]
<end of template> 

**Available Webpage Data:**
{webpage_context}

**Available Citations:**
{citations}
"""

# Open Positions section template
OPEN_POSITIONS_TEMPLATE = """Use the "Available Job Data" and "Available Hiring Info Data" (below) to fill in the template about {company_name}, with citations.
Key Requirements:
1. For in-text citations: use IEEE citation style with square brackets (e.g. "[1]").
2. Use the original citation numbers provided in the source data. Do not attempt to renumber citations.
3. Format output in markdown.
4. Do not write a preface to the report; begin your output immediately with the first line of the template.

<start of template> 
## Open Positions at {company_name}
[If there are job listings found in the "Available Job Data" provided below, list the job title of each job listing in a bullet-pointed list, with citations. If no listings found, simply output this one sentence: No open positions found in a quick scan of {company_name}'s website.]
[In a separate paragraph, if there is information regarding job openings in the "Available Hiring Info Data" provided below, detail that informaton, with citations.]
[Then, in a separate paragraph, describe what can be inferred about {company_name} based on the job listings found (only if specific job listings were found) or what can be inferred about {company_name} based on the hiring information found (only if specific hiring information was found). Pay special attention to any mention of tools, technologies or methodologies associated with the job and, if appropriate, mention the exact tools, technologies, or methodolgies by name. If neither specific job listings nor hiring information were found, simply output this one sentence: No open positions found in a quick scan of {company_name}'s website.]
[Then, in a separate paragraph, include this note (without the quotes around it): "Note: Job listings are sourced solely from {company_name}'s website."]
[Then, in a seperate paragraph, include this note (without the quotes around it): "Want more in-depth results? <a href="https://www.nofluffselling.com/contact" target="_blank">Contact us</a>"]
<end of template> 

**Available Job Data:**
{job_context}

**Available Hiring Info Data:**
{hiring_info_context}

**Available Citations:**
{citations}
"""

# News section template
NEWS_TEMPLATE = """Use the "Available News Data", "Available Webpage Data" (below) to fill in the template, creating a comprehensive sales intelligence report about {company_name}, with citations.
Key Requirements:
1. For in-text citations: use IEEE citation style with square brackets (e.g. "[1]").
2. Use the original citation numbers provided in the source data. Do not attempt to renumber citations.
3. Format output in markdown.
4. Do not write a preface to the report; begin your output immediately with the first line of the template.

<start of template> 
## {company_name} News (Last 12 Months)
[Using the "Available News Data" and "Available Webpage Data" (provided below) and your own knowledge, summarize 3-7 major news developments about {company_name} from the last 12 months that are relevant to the services and products offered by {user_company_name} which is described in the "Available User Company Report Data" included below. Cite real news data sources. For each event, summarize the event using cited, factual evidence. Then, in a second paragraph, summarize what the event infers about {company_name}. Then, in a third paragraph, summarize what the event infers about the potential value of {user_company_name}'s offerings to {company_name}. Don't use bullet-points, but do separate each event with a descriptive heading. If no news found, output "No current events found".]
[Use this format for each event:
### Descriptive News Development Title
<br>3-5 sentences news development summary, with citations
<br><b>{company_name} Impact Inference:</b> 3-5 sentences summary of what can be inferred about {company_name}.
<br><b>{user_company_name} Inference:</b> 3-5 sentences summary of what can be inferred about {company_name}'s potential use for {user_company_name}'s product/service offerings.]
<end of template> 

**Available News Data:**
{news_context}

**Available Webpage Data:**
{webpage_context}

**Available Citations:**
{citations}
"""

# Macro Trends and Shocking Statistics section template
MACRO_TRENDS_TEMPLATE = """Use the "Available Macro Data" (below) to fill in the template, creating a comprehensive sales intelligence report about {company_name}, with citations.
Key Requirements:
1. For in-text citations: use IEEE citation style with square brackets (e.g. "[1]").
2. Use the original citation numbers provided in the source data. Do not attempt to renumber citations.
3. Format output in markdown.
4. Do not write a preface to the report; begin your output immediately with the first line of the template.

<start of template> 
## Industry Macro Trends
[Using the "Available Macro Data" (provided below), and your own knowledge, synthesize up to 5 broad market (macro) trends for the industry/industries that {company_name} operates in, highlighting key events, policy changes, technological innovations, and any notable shifts in consumer behavior. Combine information from multiple data sources to deduce each market trend you synthesize and use (multiple) citations to substantiate every trend. Cite real data sources only! For each trend, detail the trend and then, in a second paragraph, summarize how the trend might impact companies in the industry. If the impact is factual, cite the source. If no trends are found, output "No macro trends found".]
[Use this format for each trend:
### Descriptive Macro Trend Title
<br>3-5 sentences trend description, with multiple citations
<br><b>Impact:</b> 3-5 sentence description of the trend's impact on companies in the industry.]

## Shocking Statistics
[If sufficient data exists within the available data sources, list up to 3 compelling statistics about the industry {company_name} operates in, with citations, that could help build rapport. These compelling/shocking industy statistics should be industry-wide, as opposed to statistics specifically about {company_name}. Don't use bullet-points, but do separate each statistic with a descriptive heading. If no statistics are found, omit this section.]
<end of template> 

**Available Macro Data:**
{macro_context}

**Available Citations:**
{citations}
"""