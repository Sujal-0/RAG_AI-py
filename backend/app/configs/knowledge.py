"""Central knowledge base configurations.

Consolidates topic metadata, trigger criteria, answers, and suggestion questions
in a single location to prevent duplication.
"""

from pydantic import BaseModel


class KnowledgeEntry(BaseModel):
    """Configuration structure representing a searchable knowledge domain."""

    intent_id: str
    title: str
    keywords: list[str]
    trigger_phrases: list[str]
    answer: str
    suggested_questions: list[str]
    threshold: float = 0.70
    is_document_aware: bool = False


KNOWLEDGE_DATABASE: list[KnowledgeEntry] = [
    KnowledgeEntry(
        intent_id="COMPANY_OVERVIEW",
        title="Company Overview",
        keywords=["overview", "mobiloitte"],
        trigger_phrases=[
            "about mobiloitte",
            "who is mobiloitte",
            "what is mobiloitte",
            "tell me about mobiloitte",
            "company overview",
            "company name",
            "name of the company",
            "name of company",
            "company's name",
            "the company name",
            "what is the company name",
            "what is the name of the company",
            "about company",
            "company history",
            "company leadership",
            "about history",
            "about leadership",
            "about organization",
            "company",
            "organization",
            "leadership",
        ],
        answer="Mobiloitte Technologies India Pvt. Ltd. is a premier, full-service software development company specializing in digital transformation, blockchain, artificial intelligence, IoT, and cloud services.",
        suggested_questions=[
            "What services does Mobiloitte provide?",
            "Where is Mobiloitte located?",
        ],
    ),
    KnowledgeEntry(
        intent_id="SERVICES",
        title="Company Services",
        keywords=["services", "capabilities"],
        trigger_phrases=[
            "what services do you offer",
            "what are your services",
            "what solutions do you provide",
            "list services",
            "enterprise software",
            "data science",
        ],
        answer="Mobiloitte offers comprehensive digital solutions including Web and Mobile Application Development, Blockchain Systems, AI/ML integrations, IoT automation, and Cloud infrastructure scaling.",
        suggested_questions=[
            "Tell me about AI services.",
            "Tell me about Blockchain services.",
        ],
    ),
    KnowledgeEntry(
        intent_id="AI_SERVICES",
        title="Artificial Intelligence Services",
        keywords=["artificial_intelligence", "machine_learning", "nlp", "chatbot"],
        trigger_phrases=[
            "tell me about artificial intelligence",
            "ai services",
            "machine learning solutions",
            "do you do ai",
        ],
        answer="Our AI division designs advanced Machine Learning models, Natural Language Processing systems, computer vision systems, smart conversational chatbots, and predictive business analytics solutions.",
        suggested_questions=[
            "Tell me about technologies.",
            "What solutions do you provide?",
        ],
    ),
    KnowledgeEntry(
        intent_id="CLOUD_SERVICES",
        title="Cloud Services",
        keywords=["cloud", "aws", "azure", "gcp", "devops"],
        trigger_phrases=[
            "tell me about cloud services",
            "aws solutions",
            "do you do cloud migration",
            "gcp and azure support",
        ],
        answer="Mobiloitte offers specialized cloud consulting, migration, infrastructure automation, DevOps integration, and managed support services using AWS, Microsoft Azure, and Google Cloud Platform.",
        suggested_questions=[
            "What technologies do you use?",
            "How can I contact support?",
        ],
    ),
    KnowledgeEntry(
        intent_id="WEB_DEVELOPMENT",
        title="Web Development Services",
        keywords=["web", "website", "frontend", "backend", "react", "node"],
        trigger_phrases=[
            "web development services",
            "do you build websites",
            "custom web applications",
        ],
        answer="We engineer highly secure, responsive, and scalable web platforms using modern architectures like React, Angular, Vue, Node.js, Python, Java, and PHP.",
        suggested_questions=[
            "What services do you provide?",
            "What technologies do you use?",
        ],
    ),
    KnowledgeEntry(
        intent_id="MOBILE_DEVELOPMENT",
        title="Mobile Development Services",
        keywords=["mobile", "flutter", "ios", "android", "app"],
        trigger_phrases=[
            "mobile app development",
            "do you build apps",
            "flutter development services",
            "ios and android apps",
        ],
        answer="Mobiloitte develops high-performance native iOS and Android apps, as well as cross-platform solutions using Flutter, React Native, and Swift/Kotlin.",
        suggested_questions=["Do you build websites?", "What technologies do you use?"],
    ),
    KnowledgeEntry(
        intent_id="BLOCKCHAIN",
        title="Blockchain Services",
        keywords=["blockchain", "solidity", "smart_contract", "web3", "ethereum"],
        trigger_phrases=[
            "blockchain development",
            "do you do web3",
            "smart contracts solidity",
        ],
        answer="We build secure decentralized applications, custom smart contracts, token minting engines, private blockchain ledgers, and end-to-end Web3 ecosystems.",
        suggested_questions=[
            "Tell me about AI services.",
            "What solutions do you provide?",
        ],
    ),
    KnowledgeEntry(
        intent_id="IOT",
        title="Internet of Things Services",
        keywords=["iot", "internet_of_things", "sensor", "firmware", "device"],
        trigger_phrases=[
            "internet of things support",
            "iot solutions",
            "smart device integration",
        ],
        answer="Mobiloitte delivers robust IoT solutions including smart device prototyping, firmware programming, sensor data integration, and enterprise IoT dashboards.",
        suggested_questions=[
            "What services do you offer?",
            "Tell me about cloud services.",
        ],
    ),
    KnowledgeEntry(
        intent_id="CAREERS",
        title="Careers",
        keywords=["careers", "jobs", "hiring", "openings", "human_resources", "hr"],
        trigger_phrases=[
            "careers at mobiloitte",
            "job openings",
            "how to apply for a job",
            "are you hiring",
            "join mobiloitte",
            "human resources",
        ],
        answer="Join our team at Mobiloitte! We offer exciting careers across development, design, project management, and business development. Check our website or contact HR to apply.",
        suggested_questions=["Do you offer internships?", "How can I contact HR?"],
    ),
    KnowledgeEntry(
        intent_id="INTERNSHIP",
        title="Internship Opportunities",
        keywords=["internship", "intern", "internships"],
        trigger_phrases=[
            "internship opportunities",
            "do you hire interns",
            "student training programs",
        ],
        answer="Mobiloitte offers structured, hands-on internship programs for fresh graduates and students looking to specialize in Blockchain, AI, Mobile Apps, or Web Development.",
        suggested_questions=["Are you hiring?", "What technologies do you use?"],
    ),
    KnowledgeEntry(
        intent_id="OFFICE_LOCATIONS",
        title="Office Locations",
        keywords=[
            "office_locations",
            "address",
            "branches",
            "locations",
            "headquarters",
        ],
        trigger_phrases=[
            "where are your offices",
            "office address",
            "location details",
            "where are you located",
            "office location",
            "head office",
            "delhi office",
            "noida office",
            "pune office",
            "london office",
            "location of the company",
            "locations of the company",
            "company location",
            "company locations",
            "company offices",
            "where is the company located",
            "where is mobiloitte located",
            "locations of mobiloitte",
        ],
        answer="Mobiloitte is headquartered in New Delhi, India, with regional offices in the USA, UK, and Singapore to support our global enterprise clients.",
        suggested_questions=[
            "How can I contact Mobiloitte?",
            "What is your email address?",
        ],
    ),
    KnowledgeEntry(
        intent_id="CONTACT_DETAILS",
        title="Contact Details",
        keywords=["contact_details", "phone", "email", "mail", "number"],
        trigger_phrases=[
            "how to contact you",
            "phone number",
            "email address",
            "website link",
            "website",
            "company contact",
            "contact the company",
            "contact company",
            "mobiloitte contact",
            "contact mobiloitte",
            "company phone number",
            "company email",
            "general contact information",
            "contact information",
        ],
        answer="You can contact Mobiloitte via email at contact@mobiloitte.com, by phone at +91-9999999999, or visit our website at https://www.mobiloitte.com.",
        suggested_questions=[
            "Where are your offices?",
            "What services do you provide?",
        ],
    ),
    KnowledgeEntry(
        intent_id="COMPANY_VISION",
        title="Company Vision",
        keywords=["vision"],
        trigger_phrases=[
            "company vision",
            "what is your vision",
            "where do you see the company",
            "vision of the company",
            "vision of company",
            "company's vision",
            "vision of mobiloitte",
            "mobiloitte vision",
        ],
        answer="Our vision is to empower global businesses by creating robust, high-performance digital ecosystems using cutting-edge next-generation technologies.",
        suggested_questions=[
            "What is the company mission?",
            "What are your core values?",
        ],
    ),
    KnowledgeEntry(
        intent_id="MISSION",
        title="Company Mission",
        keywords=["mission"],
        trigger_phrases=[
            "company mission",
            "what is your mission",
            "what drives you",
            "mission of the company",
            "mission of company",
            "company's mission",
            "mission of mobiloitte",
            "mobiloitte mission",
        ],
        answer="Our mission is to deliver high-quality, scalable digital solutions with rapid turnaround times, creating maximum value for our clients and partners.",
        suggested_questions=[
            "What is the company vision?",
            "What are your core values?",
        ],
    ),
    KnowledgeEntry(
        intent_id="VISION_MISSION",
        title="Vision and Mission",
        keywords=["vision", "mission"],
        trigger_phrases=[
            "vision and mission",
            "vision & mission",
            "mission and vision",
            "mission & mission",
            "vision and mission of the company",
            "vision and mission of mobiloitte",
        ],
        answer="Vision:\nOur vision is to empower global businesses by creating robust, high-performance digital ecosystems using cutting-edge next-generation technologies.\n\nMission:\nOur mission is to deliver high-quality, scalable digital solutions with rapid turnaround times, creating maximum value for our clients and partners.",
        suggested_questions=[
            "What are your core values?",
            "What services does Mobiloitte provide?",
        ],
    ),
    KnowledgeEntry(
        intent_id="VALUES",
        title="Company Values",
        keywords=["values", "principles"],
        trigger_phrases=[
            "company values",
            "what are your values",
            "core principles",
            "values of the company",
            "values of company",
            "company's values",
            "values of mobiloitte",
            "mobiloitte values",
        ],
        answer="At Mobiloitte, we value innovation, integrity, transparency, client satisfaction, and continuous learning to adapt to the changing technology landscape.",
        suggested_questions=[
            "What is the company culture like?",
            "What is your mission?",
        ],
    ),
    KnowledgeEntry(
        intent_id="CULTURE",
        title="Company Culture",
        keywords=["culture", "workplace"],
        trigger_phrases=[
            "work culture",
            "life at mobiloitte",
            "workplace environment",
            "culture of the company",
            "culture of company",
            "company's culture",
            "culture of mobiloitte",
            "mobiloitte culture",
        ],
        answer="We foster a collaborative, highly creative, and diverse workplace culture that encourages software developers and engineers to innovate and solve real-world problems.",
        suggested_questions=["What are your core values?", "Are you hiring?"],
    ),
    KnowledgeEntry(
        intent_id="TECHNOLOGIES",
        title="Technologies Used",
        keywords=["technologies", "tech", "stack"],
        trigger_phrases=[
            "what technologies do you use",
            "tech stack",
            "programming languages supported",
        ],
        answer="We leverage a modern tech stack including Python, Javascript/Typescript, Swift, Go, Solidity, Flutter, React, AWS, Docker, Kubernetes, and TensorFlow.",
        suggested_questions=[
            "Tell me about AI services.",
            "Tell me about Blockchain services.",
        ],
    ),
    KnowledgeEntry(
        intent_id="TRAINING",
        title="Employee Training",
        keywords=["training", "upskill", "certifications"],
        trigger_phrases=[
            "training programs",
            "how do you upskill employees",
            "learning and development",
        ],
        answer="Mobiloitte provides continuous learning programs, technical certifications support, and mentorship platforms to ensure our team stays expert in modern technologies.",
        suggested_questions=[
            "What is the company culture like?",
            "What are your career openings?",
        ],
    ),
    KnowledgeEntry(
        intent_id="SUPPORT",
        title="Client Support",
        keywords=["support", "maintenance", "helpdesk"],
        trigger_phrases=[
            "client support options",
            "maintenance plans",
            "helpdesk contact",
            "support email",
        ],
        answer="We offer round-the-clock client support, comprehensive software maintenance SLAs, and post-deployment monitoring to ensure platform reliability. Contact us at support@mobiloitte.com.",
        suggested_questions=[
            "How can I contact contact details?",
            "Where are your offices?",
        ],
    ),
    KnowledgeEntry(
        intent_id="DEPARTMENTS",
        title="Company Departments",
        keywords=["departments", "engineering", "hr", "sales"],
        trigger_phrases=[
            "departments",
            "company departments",
            "list departments",
            "engineering department",
            "hr department",
            "what are the departments",
        ],
        answer="Mobiloitte's key organizational departments include Software Engineering, Human Resources (HR), Business Development, UI/UX Design, Quality Assurance (QA), and Project Management.",
        suggested_questions=[
            "Are you hiring?",
            "What technologies do you use?",
        ],
    ),
    KnowledgeEntry(
        intent_id="FOUNDER",
        title="Company Founder & CEO",
        keywords=["founder", "ceo", "established", "jagdish"],
        trigger_phrases=[
            "founder",
            "who is the founder",
            "founder of the company",
            "ceo of the company",
            "who is the ceo",
            "ceo",
            "founded",
        ],
        answer="Mobiloitte was founded in 2009 by Mr. Jagdish Harsh, who serves as the Group CEO and leader of our global technology services.",
        suggested_questions=[
            "What is the company history?",
            "What is your vision?",
        ],
    ),
]

