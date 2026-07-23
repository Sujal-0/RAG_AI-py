"""Static Corporate Registry.

Provides immutable, definitive knowledge blocks for instant 
Retrieval routing without touching the dynamic PostgreSQL database.
"""

company_basics = {
    "mission": "To empower global businesses with production-ready AI solutions, enterprise software platforms, cloud-native applications, and intelligent automation workflows that drive measurable ROI from technology strategy to final execution.",
    "vision": "To architect the future of digital advantage by building secure, scalable, and governed AI systems that transform enterprise operations globally.",
    "security": "Mobiloitte enforces total security-by-design principles across all deployments, including mandatory data encryption in transit via TLS/SSL and at rest via AES-256, continuous OWASP Top 10 threat detection, VAPT smart contract code audits, and comprehensive zero-trust cybersecurity compliance.",
    "cloud": "Mobiloitte provides scalable cloud optimization, serverless architectures, multi-region failover automation, and DevOps/MLOps pipelines across AWS, Azure, and Google Cloud Platform, reducing infrastructure overhead while optimizing performance.",
    "business roi": "Mobiloitte delivers clear business ROI by utilizing automated cloud infrastructure optimization, microservices modernizations, and elite agile sprint timelines to reduce overall engineering costs and accelerate time-to-market.",
    "cloud native": "Our cloud-native vertical focuses on enterprise container orchestration using Docker and Kubernetes, alongside auto-scaling serverless architectures across AWS, Microsoft Azure, and GCP.",
    "aws": "Mobiloitte is a specialist in cloud infrastructure, provisioning high-availability AWS ecosystems using Lambda, EC2, ECS, RDS, and infrastructure-as-code automation via Terraform.",
    "blockchain": "Mobiloitte is a recognized market innovator in ledger decentralization, creating secure public, private, and consortium networks using Hyperledger, Ethereum, and Polygon, alongside Solidity/Rust smart contracts and RWA tokenization.",
    "ceo": "Jagdish Harsh is the Founder, Managing Director, and CEO of Mobiloitte. He founded the company in 2009 with a focus on strong business ethics, top-notch quality, and 100% client satisfaction.",
    "locations": "Mobiloitte is headquartered at D-115, Okhla Phase-1 in New Delhi, India. We also operate global offices in Pune (India), Wilmington, MA (USA), Milton Keynes (UK), Singapore, Dubai (UAE), and Centurion (South Africa).",
    "services": "Mobiloitte specializes in Enterprise AI & RAG systems, Software/Web/Mobile Product Engineering (React, Node, Python), Blockchain/Web3 solutions, and Cloud/DevOps infrastructure orchestration.",
    "history": "Founded in 2009 by Jagdish Harsh, Mobiloitte started in a small Delhi office and has grown into a 1,000+ person team across APAC, EMEA, and North America, delivering solutions for 5,000+ projects globally.",
    "core_values": "Strong Business Ethics (integrity in all client and internal interactions), Top-Notch Quality Work (delivering measurable enterprise ROI), Customer-First Engineering (prioritizing user experience and compliance), and Security & Transparency (zero-trust architectures and tamper-resistant audit trails).",
    "helpline": "Global Helpline (UK/Singapore): 1800-5691801. Corporate Website: https://www.mobiloitte.com/",
    "certifications": "ISO 9001 (Quality Management), ISO 27001 (Information Security Management), SOC 2 (System and Organization Controls for Data Compliance), HIPAA (Healthcare Data Compliance), GDPR (General Data Protection Regulation), and DPDP (Digital Personal Data Protection Act Compliance).",
    "careers": "Mobiloitte actively recruits elite technical professionals across Engineering, UI/UX Design, and AI Analytics divisions. Current active openings include Frontend React Engineers, UI/UX Product Designers, and AI Data Scientists. To apply, please send your resume and credentials to hr@mobiloitte.com or contact Internal Telephone Extension Line 204."
}

# Hardcoded Mobiloitte Facts
STATIC_KNOWLEDGE = {
    "company_basics": company_basics,
    "tech_stack": {
        "cloud native": company_basics["cloud native"],
        "aws": company_basics["aws"],
        "blockchain": company_basics["blockchain"]
    },
    "offices": {
        "new_delhi": "D-115, Okhla Phase-1, New Delhi, India. Focus: Global Headquarters, Executive Management, AI/ML Research, Core Software Development Lab.",
        "pune": "Hinjewadi Infotech Park, Pune, Maharashtra, India. Focus: Enterprise Product Engineering, Microservices Development, Cloud Operations.",
        "bengaluru": "Electronic City, Bengaluru, Karnataka, India. Focus: Web3 Ecosystems, Decentralized Applications, IoT Firmware, Smart Contract Development.",
        "london": "Suite 415c, Margaret Powell House, Midsummer Blvd, Milton Keynes, MK9 3BN, UK. Focus: European HQ, RegTech Solutions, FCA Compliance Reporting, Financial Crime Intelligence.",
        "singapore": "1 Raffles Place, #34-04, One Raffles Place, Singapore 048616. Focus: APAC Regional Headquarters, Cross-Border Enterprise Operations."
    },
    "core_faqs": {
        "what is mobiloitte": "Mobiloitte is an enterprise-grade digital engineering company specializing in AI Development, Blockchain architectures, IoT telemetry, Cloud Native modernizations, Mobile/Web software, and global digital transformation.",
        "what cloud providers does mobiloitte support": "Mobiloitte fully supports and orchestrates infrastructure migrations across Amazon Web Services (AWS), Microsoft Azure, and Google Cloud Platform (GCP) using Infrastructure as Code (Terraform).",
        "what is the sdlc framework used by mobiloitte": "Mobiloitte follows a strict 6-phase roadmap for enterprise delivery: 1. Discovery & Audit (Requirements Mapping), 2. Security Blueprint (Zero-Trust Setup), 3. Agile Sprints (2-week parallel development cycles), 4. Build & Integration (API/Middleware assembly), 5. QA & Security Testing (VAPT validation), and 6. Controlled Rollout (Phased deployment & FinOps optimization).",
        "does mobiloitte offer blockchain services": "Yes, Mobiloitte provides complete Web3 engineering, including Solidity and Rust Smart Contracts, private permissioned configurations (Hyperledger, Corda), public decentralized networks, Multi-sig/MPC key management, and smart contract security VAPT audits.",
        "what is converiqo": "Converiqo is Mobiloitte's proprietary Unified Agentic AI BOT Platform designed to deploy autonomous AI agents safely across enterprise workflows using RAG-First knowledge grounding and strict data access logging.",
        "how does mobiloitte handle cybersecurity": "Cybersecurity is built as an architecture baseline rather than an add-on. We enforce agentless Zero-Trust models, identity verification at every API call, end-to-end data encryption, comprehensive threat modeling, and automated ISO27001/SOC2 compliance monitoring.",
        "can mobiloitte build offline mobile apps": "Yes, Mobiloitte builds high-stakes mobile applications incorporating Offline-First Sync Workflows, allowing field operations to continue working seamlessly without internet dependency and syncing telemetry data automatically once connection recovers.",
        "what is mobiloittes average cloud uptime": "Mobiloitte targets and consistently achieves a 99.97% System Uptime SLA across all modular, serverless, and Kubernetes-orchestrated cloud-native architectures.",
        "does mobiloitte assist with uk regulatory compliance": "Yes, Mobiloitte UK specializes in RegTech solutions, including FCA (Financial Conduct Authority) Risk Management & Reporting and advanced Financial Crime Intelligence systems."
    }
}

# Canonical Routing Keys mapped to their string response
ROUTING_KEYS = {
    "history": STATIC_KNOWLEDGE["company_basics"]["history"],
    "mission": STATIC_KNOWLEDGE["company_basics"]["mission"],
    "vision": STATIC_KNOWLEDGE["company_basics"]["vision"],
    "core_values": STATIC_KNOWLEDGE["company_basics"]["core_values"],
    "helpline": STATIC_KNOWLEDGE["company_basics"]["helpline"],
    "certifications": STATIC_KNOWLEDGE["company_basics"]["certifications"],
    "offices": "\n".join(f"- {k.replace('_', ' ').title()}: {v}" for k, v in STATIC_KNOWLEDGE["offices"].items()),
    "tell me about mobiloitte": STATIC_KNOWLEDGE["core_faqs"]["what is mobiloitte"],
    **STATIC_KNOWLEDGE["core_faqs"],
    **STATIC_KNOWLEDGE["tech_stack"],
    "business roi": STATIC_KNOWLEDGE["company_basics"]["business roi"],
    "locations": STATIC_KNOWLEDGE["company_basics"]["locations"]
}

# Add normalized keys for RapidFuzz matching (e.g., removing punctuation)
FUZZY_KEYS = {k.lower().strip(): v for k, v in ROUTING_KEYS.items()}
