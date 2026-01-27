import json
import random
from typing import Dict, List, Optional, Any
from datetime import datetime
import os
from pathlib import Path

# Try to use available AI models
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    from langchain.llms import LlamaCpp
    from langchain.prompts import PromptTemplate
    from langchain.chains import LLMChain
    LLAMA_AVAILABLE = True
except ImportError:
    LLAMA_AVAILABLE = False

class AIPaperGenerator:
    """AI-powered academic paper generator"""
    
    def __init__(self, model_type: str = "openai", api_key: Optional[str] = None):
        self.model_type = model_type
        self.api_key = api_key
        self.journal_topics = self._load_journal_topics()
        self.research_areas = [
            "Artificial Intelligence", "Machine Learning", "Data Science",
            "Computer Vision", "Natural Language Processing", "Cybersecurity",
            "Internet of Things", "Blockchain Technology", "Quantum Computing",
            "Renewable Energy", "Biotechnology", "Neuroscience",
            "Environmental Science", "Public Health", "Economics",
            "Psychology", "Sociology", "Political Science"
        ]
        
        if model_type == "openai" and OPENAI_AVAILABLE and api_key:
            openai.api_key = api_key
        elif model_type == "llama" and LLAMA_AVAILABLE:
            self._setup_llama_model()
    
    def _load_journal_topics(self) -> Dict:
        """Load journal topics from JSON file"""
        topics_path = Path("data/journals/journal_topics.json")
        if topics_path.exists():
            with open(topics_path, 'r') as f:
                return json.load(f)
        else:
            # Default topics if file doesn't exist
            return {
                "computer_science": [
                    "Advances in Deep Learning Architectures",
                    "Explainable AI in Healthcare",
                    "Quantum Machine Learning Applications",
                    "Edge Computing for IoT Systems",
                    "Blockchain for Data Security"
                ],
                "engineering": [
                    "Sustainable Energy Solutions",
                    "Smart Material Development",
                    "Robotics and Automation",
                    "Biomedical Engineering Innovations",
                    "Civil Infrastructure Monitoring"
                ],
                "science": [
                    "Climate Change Mitigation Strategies",
                    "Genome Editing Technologies",
                    "Space Exploration Advancements",
                    "Renewable Energy Storage",
                    "Biodiversity Conservation"
                ]
            }
    
    def _setup_llama_model(self):
        """Setup local Llama model"""
        model_path = "models/llama-2-7b-chat.Q4_K_M.gguf"
        if os.path.exists(model_path):
            self.llm = LlamaCpp(
                model_path=model_path,
                temperature=0.7,
                max_tokens=2000,
                top_p=0.95,
                n_ctx=4096,
                verbose=False
            )
        else:
            print(f"Llama model not found at {model_path}")
            self.llm = None
    
    def generate_paper_title(self, student_field: Optional[str] = None) -> str:
        """Generate an academic paper title"""
        if not student_field:
            student_field = random.choice(self.research_areas)
        
        field_key = self._categorize_field(student_field)
        topics = self.journal_topics.get(field_key, self.journal_topics["computer_science"])
        
        base_topic = random.choice(topics)
        
        title_formats = [
            f"A Comprehensive Study of {base_topic}",
            f"Exploring {base_topic}: New Perspectives and Applications",
            f"{base_topic}: Challenges and Opportunities",
            f"Advances in {base_topic}: A Systematic Review",
            f"Implementing {base_topic} in Modern Systems"
        ]
        
        return random.choice(title_formats)
    
    def _categorize_field(self, field: str) -> str:
        """Categorize student field into general topic"""
        field_lower = field.lower()
        
        if any(word in field_lower for word in ['cs', 'computer', 'software', 'ai', 'ml', 'data']):
            return "computer_science"
        elif any(word in field_lower for word in ['eng', 'mechanical', 'electrical', 'civil', 'chemical']):
            return "engineering"
        elif any(word in field_lower for word in ['science', 'physics', 'chemistry', 'biology', 'math']):
            return "science"
        else:
            return "computer_science"  # default
    
    def generate_abstract(self, title: str, student_name: str) -> str:
        """Generate paper abstract using AI"""
        
        if self.model_type == "openai" and OPENAI_AVAILABLE and self.api_key:
            return self._generate_with_openai(title, student_name)
        elif self.model_type == "llama" and self.llm:
            return self._generate_with_llama(title, student_name)
        else:
            return self._generate_fallback_abstract(title, student_name)
    
    def _generate_with_openai(self, title: str, student_name: str) -> str:
        """Generate abstract using OpenAI API"""
        try:
            prompt = f"""
            Generate a professional academic abstract for a research paper titled: "{title}"
            
            Requirements:
            1. Author: {student_name}
            2. Length: 150-200 words
            3. Include: Background, Methodology, Results, Conclusion
            4. Tone: Formal academic
            5. Keywords: Include 3-5 relevant keywords
            
            Abstract:
            """
            
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are an academic paper writing assistant."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=300
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"OpenAI API error: {e}")
            return self._generate_fallback_abstract(title, student_name)
    
    def _generate_with_llama(self, title: str, student_name: str) -> str:
        """Generate abstract using local Llama model"""
        try:
            template = """
            Generate a professional academic abstract for this research paper:
            
            Title: {title}
            Author: {author}
            
            Requirements:
            - Length: 150-200 words
            - Include: Background, Methodology, Results, Conclusion
            - Formal academic tone
            - Include 3-5 keywords
            
            Abstract:
            """
            
            prompt = PromptTemplate(
                template=template,
                input_variables=["title", "author"]
            )
            
            chain = LLMChain(llm=self.llm, prompt=prompt)
            result = chain.run(title=title, author=student_name)
            
            return result.strip()
            
        except Exception as e:
            print(f"Llama generation error: {e}")
            return self._generate_fallback_abstract(title, student_name)
    
    def _generate_fallback_abstract(self, title: str, student_name: str) -> str:
        """Generate a fallback abstract without AI"""
        current_year = datetime.now().year
        
        fallback_abstract = f"""
        ABSTRACT
        
        This research paper, titled "{title}", presents a comprehensive analysis of current trends 
        and future directions in the field. Authored by {student_name}, the study investigates 
        key challenges and proposes innovative solutions based on empirical evidence and 
        theoretical frameworks.
        
        The methodology incorporates both quantitative and qualitative approaches, 
        including case studies, statistical analysis, and systematic literature review. 
        Preliminary results indicate significant potential for practical applications 
        and highlight areas for further research.
        
        This contribution aims to advance academic discourse and provide actionable 
        insights for researchers and practitioners in the field. The findings suggest 
        promising avenues for future exploration and development.
        
        Keywords: innovation, methodology, analysis, application, future research
        
        © {current_year} {student_name}. All rights reserved.
        """
        
        return fallback_abstract
    
    def generate_paper_content(self, title: str, abstract: str, student_name: str) -> Dict[str, Any]:
        """Generate full paper structure with sections"""
        
        sections = {
            "title": title,
            "author": student_name,
            "date": datetime.now().strftime("%B %d, %Y"),
            "abstract": abstract,
            "introduction": self._generate_section("Introduction", title, student_name),
            "literature_review": self._generate_section("Literature Review", title, student_name),
            "methodology": self._generate_section("Methodology", title, student_name),
            "results": self._generate_section("Results", title, student_name),
            "discussion": self._generate_section("Discussion", title, student_name),
            "conclusion": self._generate_section("Conclusion", title, student_name),
            "references": self._generate_references(),
            "acknowledgments": f"The author, {student_name}, acknowledges the support received during this research.",
            "contact": f"Correspondence: {student_name}"
        }
        
        return sections
    
    def _generate_section(self, section_name: str, title: str, author: str) -> str:
        """Generate content for a specific section"""
        
        section_templates = {
            "Introduction": f"""
            This paper, titled "{title}", introduces a comprehensive examination of 
            contemporary issues and emerging trends. Authored by {author}, the research 
            aims to address critical gaps in current understanding and propose novel 
            approaches for advancement in the field. The significance of this study 
            lies in its potential to influence both theoretical frameworks and 
            practical applications.
            """,
            
            "Literature Review": f"""
            A thorough review of existing literature reveals diverse perspectives 
            on the subject matter. Previous studies have established foundational 
            concepts while identifying areas requiring further investigation. 
            This section synthesizes key findings from peer-reviewed publications, 
            conference proceedings, and authoritative sources to contextualize 
            the current research within the broader academic discourse.
            """,
            
            "Methodology": f"""
            The research methodology employed in this study combines multiple 
            approaches to ensure comprehensive analysis. Data collection involved 
            systematic sampling techniques, while analysis utilized both statistical 
            tools and qualitative assessment frameworks. Ethical considerations 
            were strictly adhered to throughout the research process, ensuring 
            validity and reliability of the findings.
            """,
            
            "Results": f"""
            Analysis of collected data yielded significant insights. Key findings 
            demonstrate clear patterns and relationships relevant to the research 
            questions. Quantitative results are presented through statistical 
            measures, while qualitative findings offer nuanced understanding 
            of complex phenomena. These results form the basis for subsequent 
            discussion and conclusions.
            """,
            
            "Discussion": f"""
            The implications of these findings are multifaceted. Results align 
            with certain aspects of existing theories while challenging others. 
            Practical applications of these insights are explored, along with 
            limitations that suggest directions for future research. This discussion 
            situates the findings within both academic and practical contexts.
            """,
            
            "Conclusion": f"""
            In conclusion, this research contributes valuable perspectives to 
            the field. The study confirms several hypotheses while revealing 
            unexpected relationships that merit further investigation. 
            Recommendations for practitioners and researchers are provided, 
            along with suggestions for extending this work in future studies.
            """
        }
        
        return section_templates.get(section_name, "")
    
    def _generate_references(self) -> List[str]:
        """Generate sample academic references"""
        references = [
            "Smith, J., & Johnson, A. (2023). Advances in Modern Research Methods. Academic Press.",
            "Chen, L., et al. (2022). Computational Approaches to Problem Solving. Journal of Computing, 45(2), 123-145.",
            "Garcia, M. (2021). Theoretical Frameworks in Contemporary Science. Springer.",
            "Williams, R., & Brown, K. (2020). Empirical Studies and Their Applications. Research Quarterly, 78(4), 567-589.",
            "Patel, S. (2019). Innovative Methodologies in Academic Research. Cambridge University Press."
        ]
        
        return references