"""User company analysis report templates and prompts."""

# Required sections for report validation
# These sections are used in the validate_user_report_content method to ensure that
# generated reports contain all necessary components for effective sales enablement.
# Each section serves a specific purpose in understanding the company's offering:
# - Product capabilities: Details what the product can do
# - Unique selling props: Highlights key differentiators
# - Market positioning: Shows competitive stance
# - Company strengths: Emphasizes core advantages
# - Customer outcomes: Demonstrates proven value
# - Pricing structure: Shows cost model
USER_REQUIRED_SECTIONS = [
    "Product capabilities and features",
    "Unique selling propositions",
    "Market positioning",
    "Company strengths",
    "Customer success metrics",
    "Pricing and packaging"
]

# Key focus areas for adaptive query generation prompt
# These focus areas are used in the generate_adaptive_queries method in graph.py to generate
# targeted questions about the user's company and products. The method uses these areas to create
# a prompt for an LLM that generates specific questions to gather comprehensive product information.
# Each focus area represents a critical aspect of understanding the company's offerings:
# 1. Product capabilities - To understand the full feature set
# 2. Technical specs - To understand implementation requirements
# 3. Implementation process - To understand deployment and support
# 4. Competitive advantages - To understand market differentiation
# 5. Market fit - To understand ideal customer profiles
# 6. Customer outcomes - To understand proven value
# 7. Pricing models - To understand cost structure
USER_FOCUS_AREAS = [
    "The product's full capabilities and features",
    "Technical specifications and requirements",
    "Implementation and support processes",
    "Competitive advantages with specific evidence",
    "Target market fit and success stories",
    "Customer outcomes and ROI metrics",
    "Pricing models and packaging options"
]

# Fallback queries for user company research
# These queries are used as a backup in the generate_fallback_queries method when
# the adaptive query generation fails. They are designed to cover essential aspects
# of understanding the user's product and company capabilities:
# - Product features and capabilities
# - Technical requirements and integration
# - Deployment and implementation
# - Support and training
# - Competitive advantages
# - Customer success metrics
# - Pricing structure
USER_FALLBACK_QUERIES = [
    "What are the complete features and capabilities of our product?",
    "What technical specifications and requirements are needed?",
    "What integration capabilities and APIs are available?",
    "What deployment options and flexibility do we offer?",
    "What security features and compliance certifications do we have?",
    "What is our pricing model and package structure?",
    "What specific customer success stories and ROI metrics can we reference?",
    "What is our implementation methodology and timeline?",
    "What training and support options do we provide?",
    "What specific evidence differentiates us from competitors?",
    "What quantifiable outcomes have customers achieved?",
    "What are our partnership programs and ecosystem benefits?"
]

# Key sections for adaptive query generation
# These sections guide the RAG process in generating targeted queries about the
# user's company and products. They are used in the generate_adaptive_queries
# method to focus the search on specific aspects that are most relevant for
# sales enablement and customer engagement:
# - Product features: To understand capabilities
# - Technical specs: To assess implementation needs
# - Integration: To understand connectivity options
# - Deployment: To know implementation options
# - Security: To address compliance needs
# - Pricing: To understand cost structure
# - Success stories: To demonstrate value
# - Implementation: To set expectations
# - Support: To show ongoing assistance
# - Partners: To highlight ecosystem
# - Advantages: To emphasize differentiators
# - Markets: To identify target customers
# - Outcomes: To prove value
USER_ADAPTIVE_QUERY_SECTIONS = [
    "product features and capabilities",
    "technical specifications and requirements",
    "integration capabilities and APIs",
    "deployment options and flexibility",
    "security features and compliance",
    "pricing models and packages",
    "customer success stories with metrics",
    "implementation methodology",
    "training and support offerings",
    "partner ecosystem benefits",
    "competitive advantages with evidence",
    "target market segments",
    "quantifiable customer outcomes"
]

# Key sections for RAG queries
# These sections are used in the execute_rag_process method to guide the retrieval
# of relevant information from collected documents. They focus on the most critical
# aspects of the user's company that could influence sales success:
# - Features: To understand product capabilities
# - Value props: To articulate benefits
# - Market fit: To identify ideal customers
# - Tech stack: To show integration possibilities
# - Advantages: To highlight differentiators
# - Milestones: To demonstrate momentum
# - Customers: To prove market acceptance
# - Pricing: To understand cost structure
# - Outcomes: To demonstrate value
USER_KEY_SECTIONS = [
    "product features and capabilities",
    "unique selling propositions and value props",
    "target market segments and ideal customer profiles",
    "technology stack and integrations",
    "competitive advantages with evidence",
    "recent company milestones and achievements",
    "customer success stories with metrics",
    "pricing models and packaging",
    "quantifiable customer outcomes"
]

# Report template for user company analysis
# This template is used in the generate_user_company_report method to create
# comprehensive company analysis reports. It provides a structured format that:
# 1. Ensures consistent report organization
# 2. Emphasizes critical product and company information
# 3. Maintains high standards for evidence and citations
# 4. Focuses on actionable insights for sales teams
# The template includes specific instructions for:
# - Required sections and their content
# - Citation requirements and formatting
# - Evidence standards and verification
# - Sales enablement focus
USER_REPORT_TEMPLATE = """You are a business analyst specializing in B2B sales enablement. Your goal is to produce a comprehensive, sales-focused company analysis targeted at a new salesperson within the company. The analysis should help them understand:

1. The company's background, current position, and strategic direction.
2. The products/services offered, with an emphasis on how to pitch them.
3. Key market data, including primary competitors and differentiators.
4. Ideal customer profiles and value propositions that resonate with each.
5. Go-to-market strategy, including common sales channels and partner ecosystems.
6. Recent news or major milestones that could shape sales conversations.

Use the information provided below under "Available Data," which may include data scraped from:
- The company's website
- News and press releases
- Any other publicly available information that was retrieved (e.g., job postings, user reviews, etc.)

If certain information is not available or cannot be inferred, clearly indicate that. 
Wherever relevant, incorporate or refer to "Recent News" items if provided.

**Important**: 
- Write the report in Markdown format, with clear section headers. 
- Maintain a narrative tone that reads well for a salesperson. Only use list and bullet-points where it helps convey essential info succinctly.
- Use square-bracket citations (e.g., [1], [2]) at the end of each sentence making a claim if referencing specific sources from the "Citations" section.
- For competitive claims, ALWAYS cite specific evidence showing the differentiation.
- For customer success stories, include quantifiable outcomes whenever available.
- After concluding the main sections, provide a "Citations" section with the list of references used (only those references mentioned in the text), numbered sequentially (1, 2, 3) regardless of their original RAG citation numbers.

Below is the *format template* to follow for the output (rework the bullet points into narrative form, while covering these headings in order):

---
## **Company Research Analysis: {company_name}**

### **Executive Summary**
- Brief overview of the company, including founding year (if known), headquarters (if known), industry focus, and a short statement on its current market outlook.
- Mention 2-3 top takeaways a salesperson must remember (e.g., "We specialize in [X], we have [Y] funding, and we have [Z] marquee customers.").
- If available, highlight a key customer success metric or ROI figure that demonstrates value.

### **Company Overview**
- Ownership (public/private/VC-backed).
- Key executives and their backgrounds (if known).
- Employee count and relevant growth trends.
- Significant news, funding events (only if known), or strategic moves that matter to sales.

### **Products & Services**
- Main product(s) and their key capabilities or use cases.
- Highlight flagship product or service that leads most sales conversations (if known).
- New or upcoming offerings that might open up new market segments.
- Differentiators or special features that strengthen sales pitches.
- If available, include pricing model and package structure (but only if explicitly found in sources).

### **Core Value Proposition & Ideal Customer Profiles**
- What core problems does the company solve for its customers?
- Which customer types or industries benefit most (e.g., mid-market SaaS, large enterprises in finance, etc.)?
- Why do customers choose these solutions over competitor offerings?
- Include specific examples of customer pain points solved, with metrics when available.

### **Market Footprint & Competitive Landscape**
- Geographic focus and market segments targeted.
- Major competitors (search the Available Data to answer this first but, if no competitors are found, use your own knowledge to infer real-world competitors).
- How this company differentiates itself from competitors (cost, performance, features, etc.).
- Overall market positioning (e.g., "leader in data observability," "challenger with a growing presence," etc.).
- Any recognized accolades or analyst mentions relevant to the sales conversation.
- For each competitor mentioned, cite specific evidence of differentiation.

### **Go-to-Market Strategy & Sales Tactics**
- How do we typically sell? (Direct, channel partners, marketplaces, etc.)
- Typical sales cycle length or structure (if known).
- Notable partnership programs or integrations that help close deals.
- Key value drivers that resonate during sales conversations.
- If available, list common objections and recommended responses (or call out any known pitfalls in the sales cycle).
- Include specific pricing strategies or models if found in sources.

### **Recent News & Strategic Updates**
- Summaries of the most recent press releases, product launches, or any acquisitions/partnerships.
- Potential talking points for new sales outreach based on recent developments.
- Highlight any news that strengthens competitive positioning.

### **Current & Past Customers**
- List of all past and existing customers (if any), including:
  - Specific customer names with industry verticals
  - Customer reviews with quantifiable outcomes
  - Success stories with implementation details
  - Key milestones and achievements
  - ROI metrics or performance improvements when available

### **Citations**
{citations}


**Analysis Date: {analysis_date}**

**Note**: This analysis is based on publicly available information. Some conclusions are inferred from observable patterns rather than directly reported data. Any pricing information or competitive claims are based solely on publicly available sources and should be verified before use in sales conversations.
---

**Available Data:**
{combined_context}"""

# Verification prompt for user company analysis report
# This prompt is used in the verify_user_report_content method to ensure that
# generated reports meet strict requirements for accuracy and evidence.
# The prompt checks for:
# 1. Citation requirements and formatting
# 2. Evidence standards and verification
# 3. Content requirements and focus on sales enablement
USER_VERIFICATION_PROMPT = """Based on the provided context below, verify:

1. Content Requirements:
   - All claims about funding (if any) must have direct supporting evidence
   - All claims about ownership and executive leadership (if any) must cite the most recent available evidence
   - All competitive differentiation claims must cite specific evidence
   - All customer success stories must include verifiable outcomes when available
   - All pricing information must come from explicit sources
   - Each factual claim must end with a square-bracket citation [1], [2], etc.
   - Citations must be numbered sequentially (1, 2, 3) regardless of their original RAG citation numbers
   - Only cited sources should appear in the Citations section

2. Critical Information Categories:
   - Product capabilities and features
   - Market footprint and competitive positioning
   - Technology and infrastructure details
   - Recent developments and strategic moves
   - Customer success stories with outcomes
   - Pricing models (if available)
   - Partnership ecosystem

Context:
{{}}

List ONLY the missing information categories that need more research. If all critical information is present and properly cited, respond with 'COMPLETE'."""

# Content validation prompt for user company analysis report
# This prompt is used in the validate_user_report_content method to ensure that
# generated reports meet strict requirements for accuracy, evidence, and sales enablement focus.
# The prompt checks for:
# 1. Citation requirements and formatting
# 2. Evidence standards and verification
# 3. Content requirements and focus on sales enablement
USER_CONTENT_VALIDATION_PROMPT = """You are a strict fact-checker validating a company analysis report. Your job is to ensure NO fabricated or unsupported claims are made.

Validate if this company analysis report about {company_name} meets these STRICT requirements:

1. Citation Requirements (CRITICAL):
   - Each factual claim MUST have a square-bracket citation [1], [2], etc.
   - Citations MUST be numbered sequentially starting from [1] with NO gaps or duplicates
   - The Citations section MUST ONLY include sources that are explicitly referenced in the text
   - Each citation in the Citations section MUST be numbered sequentially (1, 2, 3) regardless of their original RAG citation numbers
   - Every competitive differentiation claim MUST have a specific citation
   - Every customer success story MUST cite the source of outcomes/metrics

2. Evidence Requirements (ZERO TOLERANCE FOR FABRICATION):
   - REJECT ANY funding claims (venture capital, series rounds) that lack explicit evidence in the cited source
   - REJECT ANY ownership/executive claims without recent supporting evidence
   - REJECT ANY claims about company size, revenue, or market share without clear evidence
   - REJECT ANY competitive differentiation claims without specific evidence
   - REJECT ANY customer success metrics or ROI claims without verifiable sources
   - REJECT ANY pricing information not explicitly found in sources
   - REJECT ANY speculative or forward-looking statements without clear caveats
   - For each citation, verify the claim matches what is actually stated in the source
   - REJECT if a citation's content does not support the claim being made

3. Content Requirements:
   - Company overview with ONLY verified facts
   - Products and services with specific, evidenced details
   - Market footprint and competition (only verified claims with evidence)
   - Technology and infrastructure (must be documented)
   - Recent developments (with dates and sources)
   - Customer relationships (only verified examples with outcomes)
   - Pricing information (only if explicitly sourced)
   - Partnership details (must be verified)

4. Verification Process:
   1. Check each citation number is used exactly once and in sequence
   2. Verify each cited claim against the source content
   3. Flag ANY claim that goes beyond what the source explicitly states
   4. Ensure the Citations section matches in-text citations exactly
   5. Verify all competitive claims have specific evidence
   6. Confirm all customer success metrics are sourced
   7. Validate all pricing information has explicit sources

Report:
{report_text}

Respond with:
1. PASS or FAIL
2. If FAIL, list EVERY citation issue and unsupported claim found
3. For funding/revenue/size claims, explicitly state if source evidence is missing
4. For competitive claims, verify specific evidence exists
5. For customer success stories, confirm metrics are sourced"""
