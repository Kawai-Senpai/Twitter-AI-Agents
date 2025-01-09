from typing import List, Dict, Tuple
import os
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import OpenAIEmbeddings
import chromadb
import PyPDF2
from bs4 import BeautifulSoup
from pathlib import Path

class TechnicalKnowledgeDB:
    def __init__(self, base_path: str = "./vectordbs/technical"):
        """Technical papers and documentation database"""
        self.base_path = base_path
        os.makedirs(base_path, exist_ok=True)
        
        self.embeddings = OpenAIEmbeddings()
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,  # Larger chunks for technical content
            chunk_overlap=200,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )
        
        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(path=base_path)
        self.collection = self.client.get_or_create_collection(name="technical_knowledge")
    
    def process_pdf(self, file_path: str) -> Tuple[bool, str]:
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = "\n\n".join(page.extract_text() for page in pdf_reader.pages)
                
                # Split into chunks while preserving technical context
                chunks = self.text_splitter.split_text(text)
                embeddings = self.embeddings.embed_documents(chunks)
                
                # Create metadata with technical context
                metadatas = [{
                    "source": os.path.basename(file_path),
                    "type": "technical",
                    "page_count": len(pdf_reader.pages),
                    "index": i
                } for i in range(len(chunks))]
                
                # Add to collection
                self.collection.add(
                    embeddings=embeddings,
                    documents=chunks,
                    metadatas=metadatas,
                    ids=[f"tech_{os.path.basename(file_path)}_{i}" for i in range(len(chunks))]
                )
                return True, f"Successfully processed {file_path}"
        except Exception as e:
            return False, str(e)

class BlogKnowledgeDB:
    def __init__(self, base_path: str = "./vectordbs/blog"):
        """Blog posts database"""
        self.base_path = base_path
        os.makedirs(base_path, exist_ok=True)
        
        self.embeddings = OpenAIEmbeddings()
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=750,  # Medium chunks for blog content
            chunk_overlap=150,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )
        
        self.client = chromadb.PersistentClient(path=base_path)
        self.collection = self.client.get_or_create_collection(name="blog_knowledge")
    
    def process_blog(self, file_path: str) -> Tuple[bool, str]:
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
                soup = BeautifulSoup(content, 'html.parser')
                
                # Extract main content and title
                title = soup.title.string if soup.title else ""
                main_content = soup.find('article') or soup.find('main') or soup.body
                text = main_content.get_text(separator='\n\n', strip=True)
                
                # Split into chunks preserving paragraph structure
                chunks = self.text_splitter.split_text(text)
                embeddings = self.embeddings.embed_documents(chunks)
                
                metadatas = [{
                    "source": os.path.basename(file_path),
                    "type": "blog",
                    "title": title,
                    "index": i
                } for i in range(len(chunks))]
                
                self.collection.add(
                    embeddings=embeddings,
                    documents=chunks,
                    metadatas=metadatas,
                    ids=[f"blog_{os.path.basename(file_path)}_{i}" for i in range(len(chunks))]
                )
                return True, f"Successfully processed blog {file_path}"
        except Exception as e:
            return False, str(e)

class TemporalKnowledgeDB:
    def __init__(self, base_path: str = "./vectordbs/temporal"):
        """Temporal data (tweets, transcripts) database"""
        self.base_path = base_path
        os.makedirs(base_path, exist_ok=True)
        
        self.embeddings = OpenAIEmbeddings()
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,  # Smaller chunks for temporal content
            chunk_overlap=100,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )
        
        self.client = chromadb.PersistentClient(path=base_path)
        self.collection = self.client.get_or_create_collection(name="temporal_knowledge")
    
    def process_temporal(self, file_path: str) -> Tuple[bool, str]:
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
                
                # Determine content type from filename
                content_type = "tweet" if "tweet" in file_path.lower() else \
                             "podcast" if "podcast" in file_path.lower() else \
                             "transcript"
                
                # Process differently based on content type
                if content_type == "tweet":
                    chunks = content.split('\n---\n')  # Assuming tweets are separated by ---
                else:
                    chunks = self.text_splitter.split_text(content)
                
                embeddings = self.embeddings.embed_documents(chunks)
                
                metadatas = [{
                    "source": os.path.basename(file_path),
                    "type": content_type,
                    "date": self._extract_date(file_path),  # You'd implement this based on your naming convention
                    "index": i
                } for i in range(len(chunks))]
                
                self.collection.add(
                    embeddings=embeddings,
                    documents=chunks,
                    metadatas=metadatas,
                    ids=[f"temporal_{os.path.basename(file_path)}_{i}" for i in range(len(chunks))]
                )
                return True, f"Successfully processed temporal data {file_path}"
        except Exception as e:
            return False, str(e)
    
    def _extract_date(self, file_path: str) -> str:
        """Extract date from filename - implement based on your naming convention"""
        # This is a placeholder - implement based on your actual file naming convention
        return "unknown"

def process_all_documents(base_folder: str):
    """Process all documents in their respective folders"""
    # Initialize databases
    tech_db = TechnicalKnowledgeDB()
    blog_db = BlogKnowledgeDB()
    temporal_db = TemporalKnowledgeDB()
    
    # Process technical documents
    tech_folder = os.path.join(base_folder, "Base_Data_Layer")
    for file in os.listdir(tech_folder):
        if file.endswith('.pdf'):
            success, message = tech_db.process_pdf(os.path.join(tech_folder, file))
            print(message)
    
    # Process blog posts
    blog_folder = os.path.join(base_folder, "blog_posts")
    for file in os.listdir(blog_folder):
        if file.endswith('.html'):
            success, message = blog_db.process_blog(os.path.join(blog_folder, file))
            print(message)
    
    # Process temporal data
    temporal_folder = os.path.join(base_folder, "Temporal_Data")
    for file in os.listdir(temporal_folder):
        if file.endswith('.txt'):
            success, message = temporal_db.process_temporal(os.path.join(temporal_folder, file))
            print(message)

if __name__ == "__main__":
    # Process all documents
    process_all_documents("./")