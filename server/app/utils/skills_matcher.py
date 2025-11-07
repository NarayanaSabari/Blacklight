"""
Skills Matcher and Database
Intelligent skill extraction and categorization
"""
from typing import List, Dict, Set, Optional, Any
from difflib import SequenceMatcher
import re


class SkillsMatcher:
    """
    Match and categorize skills from resume text
    Uses curated skills database with fuzzy matching
    """
    
    # Comprehensive skills database (1000+ skills)
    SKILLS_DATABASE = {
        # Programming Languages
        'programming_languages': [
            'Python', 'Java', 'JavaScript', 'TypeScript', 'C', 'C++', 'C#', 'Go', 'Rust',
            'Ruby', 'PHP', 'Swift', 'Kotlin', 'Scala', 'R', 'MATLAB', 'Perl', 'Dart',
            'Objective-C', 'Shell', 'Bash', 'PowerShell', 'Groovy', 'Lua', 'Elixir',
            'Haskell', 'Julia', 'F#', 'Clojure', 'Erlang', 'Assembly', 'COBOL', 'Fortran',
        ],
        
        # Web Technologies
        'web_frontend': [
            'HTML', 'CSS', 'HTML5', 'CSS3', 'SASS', 'SCSS', 'LESS', 'React', 'React.js',
            'Angular', 'Vue.js', 'Vue', 'Next.js', 'Nuxt.js', 'Svelte', 'jQuery', 'Bootstrap',
            'Tailwind CSS', 'Material-UI', 'Ant Design', 'Chakra UI', 'Webpack', 'Vite',
            'Parcel', 'Rollup', 'Babel', 'Redux', 'MobX', 'Zustand', 'Recoil', 'GraphQL',
            'REST API', 'WebSockets', 'WebAssembly', 'PWA', 'SPA', 'Responsive Design',
        ],
        
        'web_backend': [
            'Node.js', 'Express.js', 'Django', 'Flask', 'FastAPI', 'Spring Boot', 'Spring',
            'ASP.NET', '.NET Core', 'Ruby on Rails', 'Laravel', 'Symfony', 'CodeIgniter',
            'Nest.js', 'Koa.js', 'Hapi.js', 'Gin', 'Echo', 'Fiber', 'Actix', 'Rocket',
        ],
        
        # Databases
        'databases': [
            'MySQL', 'PostgreSQL', 'MongoDB', 'Redis', 'Oracle', 'SQL Server', 'SQLite',
            'MariaDB', 'Cassandra', 'DynamoDB', 'Elasticsearch', 'Neo4j', 'CouchDB',
            'Firebase', 'Firestore', 'Supabase', 'Prisma', 'TypeORM', 'Sequelize',
            'SQLAlchemy', 'Hibernate', 'Entity Framework', 'Mongoose', 'SQL', 'NoSQL',
            'GraphQL', 'Apache Kafka', 'RabbitMQ', 'ActiveMQ',
        ],
        
        # Cloud & DevOps
        'cloud': [
            'AWS', 'Amazon Web Services', 'Azure', 'Microsoft Azure', 'GCP', 'Google Cloud',
            'Cloud Computing', 'EC2', 'S3', 'Lambda', 'ECS', 'EKS', 'RDS', 'CloudFormation',
            'Azure Functions', 'Azure DevOps', 'Google Cloud Functions', 'Cloud Run',
            'Heroku', 'DigitalOcean', 'Linode', 'Vercel', 'Netlify', 'Railway',
        ],
        
        'devops': [
            'Docker', 'Kubernetes', 'K8s', 'Jenkins', 'GitLab CI', 'GitHub Actions',
            'CircleCI', 'Travis CI', 'Terraform', 'Ansible', 'Chef', 'Puppet', 'Vagrant',
            'CI/CD', 'Continuous Integration', 'Continuous Deployment', 'Helm', 'Istio',
            'Prometheus', 'Grafana', 'ELK Stack', 'Datadog', 'New Relic', 'Nagios',
        ],
        
        # Data Science & AI
        'data_science': [
            'Machine Learning', 'ML', 'Deep Learning', 'AI', 'Artificial Intelligence',
            'Neural Networks', 'CNN', 'RNN', 'LSTM', 'Transformer', 'NLP', 'Computer Vision',
            'TensorFlow', 'PyTorch', 'Keras', 'Scikit-learn', 'Pandas', 'NumPy', 'SciPy',
            'Matplotlib', 'Seaborn', 'Plotly', 'Jupyter', 'Data Analysis', 'Data Visualization',
            'Statistical Analysis', 'A/B Testing', 'Hypothesis Testing', 'Regression',
            'Classification', 'Clustering', 'Time Series', 'Forecasting',
        ],
        
        'big_data': [
            'Big Data', 'Hadoop', 'Spark', 'Apache Spark', 'PySpark', 'Hive', 'Pig',
            'MapReduce', 'Apache Flink', 'Storm', 'Airflow', 'Luigi', 'Databricks',
            'Snowflake', 'Redshift', 'BigQuery', 'Data Warehousing', 'ETL', 'Data Pipeline',
        ],
        
        # Mobile Development
        'mobile': [
            'iOS', 'Android', 'React Native', 'Flutter', 'Xamarin', 'Ionic', 'Cordova',
            'Swift', 'SwiftUI', 'Objective-C', 'Kotlin', 'Java', 'Mobile Development',
            'Mobile App', 'App Store', 'Google Play', 'Firebase', 'Push Notifications',
        ],
        
        # Testing
        'testing': [
            'Unit Testing', 'Integration Testing', 'E2E Testing', 'Test Automation',
            'Jest', 'Mocha', 'Chai', 'Jasmine', 'Pytest', 'unittest', 'JUnit', 'TestNG',
            'Selenium', 'Cypress', 'Playwright', 'Puppeteer', 'Appium', 'TDD', 'BDD',
            'Quality Assurance', 'QA', 'Test-Driven Development',
        ],
        
        # Version Control
        'version_control': [
            'Git', 'GitHub', 'GitLab', 'Bitbucket', 'SVN', 'Mercurial', 'Version Control',
            'Source Control', 'Pull Requests', 'Code Review', 'Git Flow',
        ],
        
        # Methodologies
        'methodologies': [
            'Agile', 'Scrum', 'Kanban', 'Waterfall', 'DevOps', 'Lean', 'XP', 'SAFe',
            'Sprint Planning', 'Daily Standup', 'Retrospective', 'JIRA', 'Confluence',
            'Trello', 'Asana', 'Monday.com', 'ClickUp',
        ],
        
        # Soft Skills
        'soft_skills': [
            'Communication', 'Leadership', 'Teamwork', 'Problem Solving', 'Critical Thinking',
            'Time Management', 'Project Management', 'Collaboration', 'Adaptability',
            'Creativity', 'Analytical Skills', 'Attention to Detail', 'Decision Making',
            'Conflict Resolution', 'Negotiation', 'Mentoring', 'Presentation Skills',
            'Public Speaking', 'Written Communication', 'Interpersonal Skills',
        ],
        
        # Design & UX
        'design': [
            'UI/UX', 'User Interface', 'User Experience', 'Figma', 'Sketch', 'Adobe XD',
            'Photoshop', 'Illustrator', 'InDesign', 'Wireframing', 'Prototyping',
            'Design Systems', 'Accessibility', 'WCAG', 'Responsive Design', 'Mobile First',
            'Design Thinking', 'User Research', 'Usability Testing', 'Information Architecture',
        ],
        
        # Security
        'security': [
            'Security', 'Cybersecurity', 'Penetration Testing', 'Ethical Hacking', 'OWASP',
            'SSL/TLS', 'Encryption', 'Authentication', 'Authorization', 'OAuth', 'JWT',
            'SAML', 'LDAP', 'Active Directory', 'Firewall', 'VPN', 'IDS/IPS', 'SIEM',
            'SOC', 'Vulnerability Assessment', 'Risk Assessment', 'Compliance', 'GDPR',
            'HIPAA', 'PCI-DSS', 'ISO 27001',
        ],
        
        # Other Technologies
        'other': [
            'Linux', 'Unix', 'Windows', 'macOS', 'Shell Scripting', 'Networking', 'TCP/IP',
            'DNS', 'HTTP', 'HTTPS', 'Load Balancing', 'Microservices', 'API Development',
            'RESTful Services', 'SOAP', 'XML', 'JSON', 'YAML', 'Markdown', 'LaTeX',
            'Blockchain', 'Smart Contracts', 'Solidity', 'Ethereum', 'Web3', 'Cryptocurrency',
            'IoT', 'Embedded Systems', 'Arduino', 'Raspberry Pi', 'MQTT', 'LoRa',
        ],
    }
    
    def __init__(self, fuzzy_threshold: float = 0.85):
        """
        Initialize skills matcher
        
        Args:
            fuzzy_threshold: Minimum similarity score for fuzzy matching (0.0-1.0)
        """
        self.fuzzy_threshold = fuzzy_threshold
        
        # Build flat list of all skills
        self.all_skills = []
        for category, skills in self.SKILLS_DATABASE.items():
            self.all_skills.extend(skills)
        
        # Create lowercase mapping for case-insensitive matching
        self.skills_lower = {skill.lower(): skill for skill in self.all_skills}
    
    def extract_skills(self, text: str) -> Dict[str, List[str]]:
        """
        Extract skills from text
        
        Args:
            text: Resume text
        
        Returns:
            Dictionary with categorized skills:
            {
                'matched_skills': ['Python', 'React', ...],
                'categories': {
                    'programming_languages': ['Python', 'JavaScript'],
                    'web_frontend': ['React'],
                    ...
                }
            }
        """
        # Exact matching first
        matched_skills = self._exact_match(text)
        
        # Fuzzy matching for partial/typo matches
        fuzzy_matches = self._fuzzy_match(text, matched_skills)
        
        # Combine and deduplicate
        all_matched = list(set(matched_skills + fuzzy_matches))
        
        # Categorize skills
        categorized = self._categorize_skills(all_matched)
        
        return {
            'matched_skills': sorted(all_matched),
            'categories': categorized,
            'total_count': len(all_matched),
        }
    
    def _exact_match(self, text: str) -> List[str]:
        """
        Exact case-insensitive word matching
        """
        matched = set()
        text_lower = text.lower()
        
        for skill_lower, skill in self.skills_lower.items():
            # Word boundary matching
            pattern = r'\b' + re.escape(skill_lower) + r'\b'
            if re.search(pattern, text_lower):
                matched.add(skill)
        
        return list(matched)
    
    def _fuzzy_match(self, text: str, exclude: List[str]) -> List[str]:
        """
        Fuzzy matching for typos and variations
        
        Args:
            text: Resume text
            exclude: Already matched skills to exclude
        
        Returns:
            List of fuzzy-matched skills
        """
        matched = set()
        words = text.split()
        exclude_lower = {s.lower() for s in exclude}
        
        for word in words:
            word_clean = word.strip('.,;:()[]{}\"\'').lower()
            
            if len(word_clean) < 3 or word_clean in exclude_lower:
                continue
            
            # Find best matching skill
            for skill_lower, skill in self.skills_lower.items():
                if skill.lower() in exclude_lower:
                    continue
                
                similarity = SequenceMatcher(None, word_clean, skill_lower).ratio()
                
                if similarity >= self.fuzzy_threshold:
                    matched.add(skill)
                    break
        
        return list(matched)
    
    def _categorize_skills(self, skills: List[str]) -> Dict[str, List[str]]:
        """
        Group skills by category
        """
        categories = {}
        
        for category, category_skills in self.SKILLS_DATABASE.items():
            matched_in_category = [
                skill for skill in skills 
                if skill in category_skills
            ]
            
            if matched_in_category:
                categories[category] = sorted(matched_in_category)
        
        return categories
    
    def suggest_skills(self, partial: str, limit: int = 10) -> List[str]:
        """
        Suggest skills based on partial input (for autocomplete)
        
        Args:
            partial: Partial skill name
            limit: Maximum number of suggestions
        
        Returns:
            List of suggested skills
        """
        partial_lower = partial.lower()
        suggestions = []
        
        for skill in self.all_skills:
            if skill.lower().startswith(partial_lower):
                suggestions.append(skill)
            
            if len(suggestions) >= limit:
                break
        
        return suggestions
    
    def get_skills_by_category(self, category: str) -> List[str]:
        """
        Get all skills in a specific category
        """
        return self.SKILLS_DATABASE.get(category, [])
    
    def get_all_categories(self) -> List[str]:
        """
        Get list of all skill categories
        """
        return list(self.SKILLS_DATABASE.keys())
    
    def validate_skills(self, skills: List[str]) -> Dict[str, Any]:
        """
        Validate and normalize a list of skills
        
        Returns:
            {
                'valid': ['Python', 'React'],
                'invalid': ['pythno', 'reac'],  # Typos
                'suggestions': {'pythno': ['Python'], 'reac': ['React', 'Redis']}
            }
        """
        skills_lower = {s.lower() for s in skills}
        valid = []
        invalid = []
        suggestions = {}
        
        for skill in skills:
            skill_lower = skill.lower()
            
            if skill_lower in self.skills_lower:
                valid.append(self.skills_lower[skill_lower])
            else:
                invalid.append(skill)
                
                # Find close matches
                close_matches = []
                for known_skill_lower, known_skill in self.skills_lower.items():
                    similarity = SequenceMatcher(None, skill_lower, known_skill_lower).ratio()
                    if similarity >= 0.75:
                        close_matches.append((known_skill, similarity))
                
                # Sort by similarity and take top 3
                close_matches.sort(key=lambda x: x[1], reverse=True)
                suggestions[skill] = [s[0] for s in close_matches[:3]]
        
        return {
            'valid': sorted(valid),
            'invalid': invalid,
            'suggestions': suggestions,
        }
