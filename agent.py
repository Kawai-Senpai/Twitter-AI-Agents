from typing import List, Dict, Any
from langchain_openai import ChatOpenAI
from langchain_community.embeddings import OpenAIEmbeddings  # Changed to match your DB creation script
from langchain.agents import create_openai_functions_agent
from langchain.agents import AgentExecutor
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.tools import Tool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.memory import ConversationBufferWindowMemory
import chromadb
from pydantic import BaseModel

class ReasoningLayer(BaseModel):
    """Structure for each reasoning layer"""
    name: str
    description: str
    thought_process: str
    conclusion: str
    confidence: float
    sources: List[Dict[str, Any]]

class VitalikAgent:
    def __init__(self):
        # Initialize LLM
        self.llm = ChatOpenAI(
            model="gpt-4-turbo-preview",
            temperature=0.7
        )
        
        # Initialize OpenAI embeddings to match your DB creation script
        self.embeddings = OpenAIEmbeddings()
        
        # Initialize memory
        self.memory = ConversationBufferWindowMemory(
            k=5,
            memory_key="chat_history",
            return_messages=True
        )
        
        # Initialize vector DB clients
        self.tech_db = chromadb.PersistentClient(path="./vectordbs/technical")
        self.blog_db = chromadb.PersistentClient(path="./vectordbs/blog")
        self.temporal_db = chromadb.PersistentClient(path="./vectordbs/temporal")
        
        # Get collections - using get_collection instead of get_or_create_collection
        self.tech_collection = self.tech_db.get_collection("technical_knowledge")
        self.blog_collection = self.blog_db.get_collection("blog_knowledge")
        self.temporal_collection = self.temporal_db.get_collection("temporal_knowledge")
        
        # Initialize tools and agent
        self.tools = self._create_tools()
        self.agent = self._create_agent()

    async def _search_technical_db(self, query: str, n_results: int = 3) -> List[Dict]:
        """Search technical knowledge base"""
        query_embedding = self.embeddings.embed_query(query)
        results = self.tech_collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results
        )
        return self._format_results(results, "technical")

    async def _search_blog_db(self, query: str, n_results: int = 3) -> List[Dict]:
        """Search blog knowledge base"""
        query_embedding = self.embeddings.embed_query(query)
        results = self.blog_collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results
        )
        return self._format_results(results, "blog")

    async def _search_temporal_db(self, query: str, n_results: int = 3) -> List[Dict]:
        """Search temporal knowledge base"""
        query_embedding = self.embeddings.embed_query(query)
        results = self.temporal_collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results
        )
        return self._format_results(results, "temporal")

    def _create_tools(self) -> List[Tool]:
        """Create tools for the agent to use"""
        return [
            Tool(
                name="search_technical_knowledge",
                description="Search through technical papers and documentation about Ethereum",
                func=self._search_technical_db
            ),
            Tool(
                name="search_blog_knowledge",
                description="Search through my blog posts and articles",
                func=self._search_blog_db
            ),
            Tool(
                name="search_temporal_knowledge",
                description="Search through my tweets and historical content",
                func=self._search_temporal_db
            ),
            Tool(
                name="analyze_layers",
                description="Analyze a topic across multiple dimensions",
                func=self._layered_analysis
            )
        ]

    def _create_agent(self) -> AgentExecutor:
        """Create the agent with custom prompt"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", """I am Vitalik Buterin, co-founder of Ethereum. I approach problems from first principles, 
            combining technical depth with philosophical and economic considerations. My communication style is 
            direct, analytical, and often draws from mathematical concepts and real-world observations.

            I frequently reference my blog posts, research papers, and previous discussions when explaining concepts. 
            I'm known for:
            - Breaking down complex problems into fundamental components
            - Considering long-term implications and incentive structures
            - Balancing technical optimization with social value
            - Being open about uncertainties and trade-offs
            - Using mathematical analogies and concrete examples
            
            Stay true to my writing style and thought process while maintaining natural conversation flow."""),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])
        
        agent = create_openai_functions_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=prompt
        )
        
        return AgentExecutor(
            agent=agent,
            tools=self.tools,
            memory=self.memory,
            verbose=True,
            handle_parsing_errors=True
        )


    def _format_results(self, results: Dict, db_type: str) -> List[Dict]:
        """Format search results with metadata"""
        return [{
            "content": doc,
            "metadata": meta,
            "type": db_type,
            "relevance_score": score
        } for doc, meta, score in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0]
        )]

    async def _layered_analysis(self, topic: str) -> List[ReasoningLayer]:
        """Perform layered analysis of a topic"""
        layers = []
        
        # Layer 1: Technical Understanding
        tech_results = await self._search_technical_db(topic)
        layers.append(ReasoningLayer(
            name="Technical Analysis",
            description="Understanding the technical fundamentals",
            thought_process=self._synthesize_thoughts(tech_results),
            conclusion=self._draw_conclusion(tech_results),
            confidence=self._calculate_confidence(tech_results),
            sources=tech_results
        ))
        
        # Layer 2: Practical Implementation
        blog_results = await self._search_blog_db(topic)
        layers.append(ReasoningLayer(
            name="Practical Implementation",
            description="Real-world applications and considerations",
            thought_process=self._synthesize_thoughts(blog_results),
            conclusion=self._draw_conclusion(blog_results),
            confidence=self._calculate_confidence(blog_results),
            sources=blog_results
        ))
        
        # Layer 3: Evolution and Context
        temporal_results = await self._search_temporal_db(topic)
        layers.append(ReasoningLayer(
            name="Temporal Context",
            description="How thinking on this topic has evolved",
            thought_process=self._synthesize_thoughts(temporal_results),
            conclusion=self._draw_conclusion(temporal_results),
            confidence=self._calculate_confidence(temporal_results),
            sources=temporal_results
        ))
        
        return layers

    def _synthesize_thoughts(self, results: List[Dict]) -> str:
        """Synthesize thoughts based on search results"""
        prompt = f"""Given this information, what would I (Vitalik) think about this?
        Consider my writing style and typical approach to such topics.
        
        Information:
        {results}"""
        
        response = self.llm.predict(prompt)
        return response

    def _draw_conclusion(self, results: List[Dict]) -> str:
        """Draw conclusions from search results"""
        prompt = f"""Based on these findings, what concrete insights would I (Vitalik) focus on?
        Frame it in my characteristic style of combining technical and philosophical perspectives.
        
        Findings:
        {results}"""
        
        response = self.llm.predict(prompt)
        return response

    def _calculate_confidence(self, results: List[Dict]) -> float:
        """Calculate confidence score based on result relevance"""
        if not results:
            return 0.0
        avg_relevance = sum(r["relevance_score"] for r in results) / len(results)
        return 1 - (avg_relevance / 2)

    async def query(self, user_input: str) -> Dict:
        """Process a user query through the agent"""
        try:
            # Get agent's response with existing chat history
            agent_response = await self.agent.ainvoke({
                "input": user_input
            })
            
            # Perform layered analysis
            analysis = await self._layered_analysis(user_input)
            
            return {
                "response": agent_response['output'],
                "context": {
                    "analysis": analysis,
                    "sources": {
                        "technical": await self._search_technical_db(user_input),
                        "blog": await self._search_blog_db(user_input),
                        "temporal": await self._search_temporal_db(user_input)
                    }
                }
            }
        except Exception as e:
            print(f"Error during query processing: {str(e)}")
            return {
                "error": str(e),
                "status": "failed"
            }

if __name__ == "__main__":
    import asyncio
    import os
    
    async def main():
        try:
            agent = VitalikAgent()
            result = await agent.query(
                "What are your thoughts on Ethereum scaling solutions?"
            )
            
            # Print only the main response by default
            print("\nResponse:", result["response"])
            
            # Optionally print technical details if requested
            # print("\nContext:", result["context"])
                
        except Exception as e:
            print(f"An error occurred: {str(e)}")
    
    asyncio.run(main())