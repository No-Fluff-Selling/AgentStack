"""Target company analysis report templates and prompts."""

# Required sections for report validation
# These sections are used in the validate_target_report_content method to ensure that
# generated reports contain all necessary components for effective sales intelligence.
# Each section serves a specific purpose in the sales process:
# - Overview: Provides context and recent developments
# - Challenges: Identifies potential pain points to address
# - Sales Angles: Maps challenges to solution opportunities
# - Citations: Ensures all claims are properly sourced
TARGET_REQUIRED_SECTIONS = [
    "Overview of Target Company Situation",
    "Key Challenges and Pain Points",
    "Strategic Sales Angles",
    "Citations"
]

# Key focus areas for adaptive query generation prompt
# These focus areas are used in the generate_adaptive_queries method in graph.py to generate
# targeted questions about potential client companies. The method uses these areas to create
# a prompt for an LLM that generates specific questions to gather sales-relevant information.
# Each focus area represents a critical aspect of understanding a potential client for B2B sales:
# 1. Current challenges - To identify pain points and needs
# 2. Decision makers - To understand the buying team
# 3. Buying process - To align with their timeline and procedures
# 4. Technical requirements - To assess fit and implementation needs
# 5. Market position - To understand competitive context
# 6. ROI expectations - To understand financial goals
# 7. Current vendor relationships - To understand existing partnerships
# 8. Security and compliance requirements - To understand regulatory needs
TARGET_FOCUS_AREAS = [
    "The company's current challenges and quantifiable impacts",
    "Decision makers and their recent initiatives",
    "Budget cycles and purchasing processes",
    "Technical requirements and integration points",
    "Security and compliance requirements",
    "Competitive pressures and market position",
    "ROI expectations and benchmarks",
    "Current vendor relationships and timelines"
]

# Fallback queries for target company research
# These queries are used as a backup in the generate_fallback_queries method when
# the adaptive query generation fails. They are designed to cover essential aspects
# of understanding a potential client company for B2B sales purposes:
# - Recent changes and initiatives
# - Decision makers and org structure
# - Business challenges and pain points
# - Technology stack and purchasing process
# - Growth plans and strategic priorities
# - Competitive pressures and market position
# - ROI expectations and benchmarks
# - Current vendor relationships and timelines
# - Security and compliance requirements
TARGET_FALLBACK_QUERIES = [
    "What major changes or initiatives has the company announced in the last 6-12 months?",
    "Who are the key decision makers and what recent initiatives are they leading?",
    "What specific business challenges or pain points is the company facing, with quantifiable impacts?",
    "What technology systems or tools do they currently use, and what are their integration points?",
    "What is their typical purchasing process, budget cycle, and ROI requirements?",
    "Are there any upcoming projects or initiatives that create urgency?",
    "What are their current vendor relationships and contract timelines?",
    "What security features and compliance requirements affect their decisions?",
    "What growth plans and strategic priorities have they publicly announced?",
    "What technical requirements or integration constraints might affect implementation?",
    "What specific evidence shows their competitive pressures and market challenges?",
    "What recent statements or actions indicate their technology preferences?"
]

# Key sections for adaptive query generation
# These sections guide the RAG process in generating targeted queries about potential
# client companies. They are used in the generate_adaptive_queries method to focus the
# search on specific aspects of the target company that are most relevant for B2B sales:
# - Company changes and initiatives: To identify timing and urgency
# - Business challenges: To understand pain points
# - Technology and tools: To assess technical fit
# - Decision makers: To identify key stakeholders
# - Process and budget: To understand buying dynamics
# - Strategic priorities: To align with company goals
# - Market position: To understand competitive context
# - Current vendor relationships: To understand existing partnerships
# - Security and compliance requirements: To understand regulatory needs
# - Growth plans: To understand future needs
# - Technical requirements: To assess fit and implementation needs
# - Implementation needs: To understand integration and deployment
# - Budget cycles: To understand financial planning
# - Competitive pressures: To understand market challenges
TARGET_ADAPTIVE_QUERY_SECTIONS = [
    "recent company changes and initiatives (6-12 months)",
    "current business challenges with quantifiable impacts",
    "technology stack and integration points",
    "decision makers and their recent initiatives",
    "purchasing process and ROI requirements",
    "strategic priorities with timelines",
    "market position with specific evidence",
    "current vendor relationships and timelines",
    "security and compliance requirements",
    "growth plans with public commitments",
    "technical requirements and constraints",
    "implementation needs and preferences",
    "budget cycles and spending patterns",
    "competitive pressures and responses"
]

# Key sections for RAG queries
# These sections are used in the execute_rag_process method to guide the retrieval
# of relevant information from collected documents. They focus on the most critical
# aspects of a potential client company that could influence a B2B sales strategy:
# - Pain points: To identify sales opportunities
# - Tech stack: To assess compatibility
# - Growth plans: To understand future needs
# - Decision makers: To target key stakeholders
# - Recent changes: To identify timing opportunities
# - Partnerships: To understand vendor relationships
# - Security and compliance requirements: To understand regulatory needs
# - Budget cycles: To understand financial planning
# - Competitive pressures: To understand market challenges
# - Technical constraints: To assess fit and implementation needs
TARGET_KEY_SECTIONS = [
    "business challenges with quantifiable impacts",
    "technology infrastructure and integration points",
    "growth initiatives with specific timelines",
    "decision makers and their recent actions",
    "recent changes with documented evidence",
    "vendor relationships with contract timelines",
    "security and compliance requirements",
    "budget cycles and ROI expectations",
    "competitive pressures with specific evidence",
    "technical constraints and preferences"
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
TARGET_REPORT_TEMPLATE = """You are a B2B sales intelligence specialist. Your task is to produce a targeted, timely, and well-justified document for a salesperson at {user_company_name} who is seeking to sell to {company_name}.

CRITICAL REQUIREMENTS:
1. EVERY factual claim must end with a square-bracket citation [1], [2], etc.
2. Citations MUST be numbered sequentially starting from [1] with NO gaps or duplicates
3. ONLY include information that is EXPLICITLY stated in the provided source documents
4. NEVER make assumptions or infer information that is not directly supported by sources
5. The Decision Makers section is OPTIONAL and should ONLY be included if you have verified evidence
6. Do not speculate or make assumptions - stick to verified facts
7. If a piece of information is not found in the source documents, DO NOT include it
8. EVERY citation number MUST correspond to a real source document in the Citations section
9. For competitive analysis, ONLY include claims with specific evidence
10. For budget/spending information, ONLY include if explicitly sourced
11. For technology claims, ONLY include with recent supporting evidence
12. For pain points, ONLY include with clear documentation

CITATION FORMAT:
- Each factual claim must end with a citation: "Company X launched product Y [1]."
- Multiple citations can be used: "Revenue grew by 25% [1] and they expanded to Europe [2]."
- Citations must point to specific sources in the Citations section
- The Citations section must list every source used, with exact URLs and dates
- Citations must be numbered sequentially: [1], [2], [3], etc.
- DO NOT skip numbers or reuse numbers
- NEVER cite a source that is not listed in the Citations section

Below is the *format template* to follow for the output:

# Sales Intelligence Report: {company_name}
**Analysis Date:** {analysis_date}

## 1. Overview of Target Company Situation
[Analyze {company_name}'s current situation, focusing on recent developments that create sales opportunities. Each statement must end with a citation [1]. Include specific events like:]
- Recent company changes or initiatives (last 6-12 months)
- New product launches or expansions
- Strategic shifts or market moves
- Notable hires or organizational changes
- Funding rounds or financial events
- Market challenges or pressures
- Quantifiable metrics when available (growth rates, revenue, etc.)

## 2. Key Challenges and Pain Points
[Based on the research, identify specific, documented challenges that {company_name} is facing. For each challenge:]
- Describe the problem with concrete details and citation [1]
- Provide quantifiable impact when available (e.g., costs, time, resources) [2]
- Show evidence of the problem from multiple sources [3]
- Explain why this creates a sales opportunity
- Show how it aligns with {user_company_name}'s solutions
- Include any public statements about the challenge [4]

## 3. Decision Makers to Approach
[IMPORTANT: ONLY include this section if you have verified evidence about specific individuals or roles. If no verified information is available, omit this section entirely.

For each verified decision maker or role:]
- Name and title with citation [1]
- Recent relevant statements or actions with citation [2]
- Areas of focus or responsibility with citation [3]
- Verified contact information with citation [4]
- Known reporting structure with citation [5]
- Recent initiatives or projects they're leading [6]

## 4. Strategic Sales Angles
[For each angle below, provide specific evidence from the research:]

### Angle 1: [Most compelling opportunity]
- Situation: [Specific details about {company_name}'s current need with citation [1]]
- Evidence: [Multiple, specific pieces of evidence that support the sales angle:]
  * [Direct quote with citation [2]]
  * [Relevant news coverage with citation [3]]
  * [Market analysis with citation [4]]
  * [Public data or metrics with citation [5]]
  * [Recent company statements with citation [6]]
- Solution: [Specific {user_company_name} offering that addresses this]
- Why Now: [Timing factors that make this urgent with citation [7]]
- ROI Potential: [If available, similar customer outcomes or industry benchmarks]
- Experience Highlight: [Specific related work that {user_company_name} has done]

### Angle 2: [Second opportunity]
[Same structure as above, with different focus]

[Add more angles if strong evidence exists]

## 5. Technology Stack and Integration Points
[Only include verified information about technologies, tools, or platforms that {company_name} uses:]
- Current technology stack with citations [1]
- Integration points and APIs in use with citations [2]
- Known limitations or gaps with citations [3]
- Recent technology changes or initiatives [4]
- Cloud infrastructure and preferences [5]
- Development frameworks and tools [6]
- Security and compliance requirements [7]

## 6. Budget and Purchasing Context
[Only include if explicitly documented:]
- Known budget cycles with citations [1]
- Recent technology investments with citations [2]
- Procurement process details with citations [3]
- Vendor evaluation criteria with citations [4]
- ROI requirements or expectations [5]

## 7. Risk Factors and Mitigation
[List specific factors that could affect the sale, each with supporting evidence:]
- Current vendor relationships with citations [1]
- Contract renewal timelines with citations [2]
- Competing internal priorities with citations [3]
- Technical limitations or constraints [4]
- Organizational challenges or changes [5]
- Regulatory or compliance requirements [6]
- Budget constraints or fiscal timing [7]

## Citations
1. [First source title] - [URL]
2. [Second source title] - [URL]
[Continue with sequential numbering]

**Analysis Date: {analysis_date}**

Note: This analysis is based solely on information from {company_name}'s public presence, news coverage, and market research."""

# Verification prompt for target company analysis
# This prompt is used in the verify_target_company_analysis method to ensure that
# the generated report meets the required standards for evidence and citations.
# It checks for:
# - Proper citation formatting and sequencing
# - Evidence support for all claims
# - Completeness of critical information categories
TARGET_VERIFICATION_PROMPT = """Based on the provided context below, verify:

1. Content Requirements:
   - All claims about decision makers and org structure must have direct supporting evidence
   - All claims about technology stack and integrations must cite the most recent available evidence
   - All claims about budget and spending must have explicit source documentation
   - All competitive analysis claims must have specific supporting evidence
   - All pain points must be documented with clear evidence
   - Each factual claim must end with a square-bracket citation [1], [2], etc.
   - Citations must be numbered sequentially (1, 2, 3) regardless of their original RAG citation numbers
   - Only cited sources should appear in the Citations section
   - All sources must include dates to ensure recency

2. Critical Information Categories:
   - Business challenges and quantifiable impacts
   - Technology stack and integration points
   - Decision makers and their recent initiatives
   - Recent developments and trigger events
   - Current vendor relationships and timelines
   - Budget cycles and purchasing processes
   - Security and compliance requirements
   - ROI expectations and benchmarks

Context:
{{}}

List ONLY the missing information categories that need more research. If all critical information is present and properly cited, respond with 'COMPLETE'."""

# Content validation prompt for target company analysis
# This prompt is used in the validate_target_company_analysis_content method to
# ensure that the generated report meets the required standards for evidence and
# citations. It checks for:
# - Proper citation formatting and sequencing
# - Evidence support for all claims
# - Completeness of critical information categories
# - Zero tolerance for fabrication or speculation
TARGET_CONTENT_VALIDATION_PROMPT = """You are a strict report validator ensuring that all information is properly cited, sourced, and actionable for sales.

Review the following report about {company_name} and verify that it meets ALL requirements:

{report_text}

VALIDATION REQUIREMENTS:
1. Citation Format and Accuracy:
   - EVERY single factual claim MUST have a citation in [square brackets]
   - Citations MUST be numbered sequentially starting from [1]
   - There MUST be NO gaps in citation numbers
   - Each citation MUST correspond to a real source in the Citations section
   - Citations section MUST include URLs and dates for all sources
   - NO fictional or made-up citations are allowed

2. Evidence Requirements:
   - ZERO unsupported claims or speculation
   - ALL information MUST come directly from source documents
   - NO inferred or assumed information
   - Decision Makers section ONLY with verified evidence
   - Technology claims ONLY with recent evidence
   - Budget/spending claims ONLY with explicit sources
   - Pain points ONLY with clear documentation
   - Competitive claims ONLY with specific evidence

3. Content Quality:
   - Quantifiable metrics when available (costs, time, resources)
   - Multiple sources for key claims when possible
   - Recent evidence (within 6-12 months) preferred
   - Clear connection between challenges and solutions
   - Specific, actionable sales opportunities
   - Documented ROI potential when available

4. Sales Intelligence Value:
   - Clear trigger events or timing factors
   - Specific decision maker insights
   - Concrete pain points with business impact
   - Actionable technology integration points
   - Verified budget and purchasing context
   - Documented risk factors and mitigations

For each requirement category:
1. Check if it passes (YES/NO)
2. If NO, list specific examples of violations

Respond with:
PASS - If ALL requirements are met
FAIL - If ANY requirement is not met

Response format:
[PASS/FAIL]
[If FAIL, list specific violations by category]
[Recommendations for addressing violations]"""
