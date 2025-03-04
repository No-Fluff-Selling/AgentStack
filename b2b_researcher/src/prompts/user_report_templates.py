"""User company analysis report templates and prompts."""

# Required sections for value proposition validation
USER_REQUIRED_SECTIONS = [
    "Value proposition",
    "Product capabilities",
    "Market differentiation",
    "Customer outcomes"
]

# Key focus areas for adaptive query generation
USER_FOCUS_AREAS = [
    "Core product capabilities and features",
    "Unique value propositions",
    "Market differentiation points",
    "Customer success metrics"
]

# Fallback queries for value proposition research
USER_FALLBACK_QUERIES = [
    "What are the main products or services offered?",
    "What unique value does the company provide to customers?",
    "How does the company differentiate itself in the market?",
    "What measurable outcomes do customers achieve?"
]

# Updated user report template focused on value proposition
USER_REPORT_TEMPLATE = """Fill in the template to generate a value proposition for {company_name} using the "Available Data" below. Note that the company being analyzed could be a consultancy, a company that sells services, a company that sells products, or a company that sells both services and products. Write your reponse in properly-formatted markdown.

Key Requirements:
1. Focus on {company_name}'s core value proposition.
2. Use factual statements supported by real citations.
3. For in-text citations: use IEEE citation style with square brackets (e.g. "[1]").
4. Use the original citation numbers provided in the source data. Do not attempt to renumber citations.
5. Include only verifiable claims from the data.
6. Format output in markdown.

<start of template>
#{company_name} Value Proposition

[Generate 3-5 paragraphs robustly detailing:
1. Core product/service offering and capabilities.
2. Unique value propositions and differentiators.
3. Target market and customer outcomes. 
Be sure that your output completely answers these questions:
1. What does the company do?
2. What differentiates the company from competitors?
3. Who is/are the target market/customers?
Use real citations from the provided data. Make strategic use of bold to highlight key points.]

## Citations (Use markdown "##" for Citations section heading. Do not use bold text for Citations section heading.)
[Format the list of citations so that each ciation is on a new line and only the number, brackets included, is hyperlinked to the corresponding source URL, and is followed by the page title and then the URL (e.g. <a href="https://webflow.bigeye.com" target="_blank">[1]</a>. [Bigeye data observability] - (https://webflow.bigeye.com)]
{citations}

**Available Data:**
{combined_context}"""

# Verification prompt for user company value proposition
USER_VERIFICATION_PROMPT = """Verify the value proposition report contains these elements using the numbered checklist. For each requirement:
1. First check structural elements
2. Then validate content quality
3. Finally verify citation integrity

[STRUCTURE] 
✅ 3-5 paragraphs + Citations section
✅ Markdown formatting
✅ Logical flow between sections

[CONTENT]
✅ Clear value proposition statement
✅ Evidence of product capabilities
✅ Market differentiation analysis
✅ Target customer outcomes
✅ Each paragraph is preceded by a descriptive heading
✅ Each paragraph incorporates multiple citations
✅ Professional business tone
✅ Many sources cited
✅ No uncited claims
✅ Strategic use of bold to highlight key points

[CITATIONS]
✅ Citations section content matches the template
✅ Each citation is on a new line

Respond using this format:
PASS: All requirements met
or
FAIL: Missing [CATEGORY] - [REQUIREMENT] (Found/Not Found)
...
"""
