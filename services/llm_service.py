import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field
from langchain.prompts import ChatPromptTemplate
from services.db_service import DBService
from typing import List, Dict, Any
from bson import ObjectId
from moviepy.editor import VideoFileClip, concatenate_videoclips
from services.google_drive_service import download_from_gdrive
from services.transcription_service import fetch_and_clean_transcript

class LLMService:
    def __init__(self):
        self.GOOGLE_API_KEY = "AIzaSyDD_1Hp4ASnKFWgDpLIs0VWpEsYIA3Efks"
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",   # can change to gemini-pro if needed
            google_api_key=self.GOOGLE_API_KEY,
            temperature=0.3
        )
        self.db = DBService()
        self.collection_name = "programs"
        self.download_video_path = "./output_videos"
        self.clipped_video_path = "./clipped_videos"

    def _get_assets(self, course_id, module_id):
        modules = self.db.find_one(self.collection_name, {"_id": ObjectId(course_id)})["courses"]
        module = [i for i in modules if i.get("_id") == ObjectId(module_id)]
        assets = []
        if module:
            assets = module[0]["module"]
        return assets
    




    def generate_article(self, course_id, module_id) -> List[str]:
        # assets = self._get_assets(course_id, module_id)
        
        # if not assets:
        #     print(f"No assets found for module {module_id}")
        #     return ""
        
        # Prepare assets context for article generation
        assets_context = ""
        # for asset in assets:
        assets_context += f"""
NestJS is a progressive Node.js framework for building efficient, reliable, and scalable server-side applications. It is built with TypeScript and combines elements of Object-Oriented Programming (OOP), Functional Programming (FP), and Functional Reactive Programming (FRP).
Here are some key aspects of NestJS:

    Architectural Inspiration:
    NestJS is heavily inspired by Angular's modular architecture, promoting a structured and organized approach to application development. It utilizes concepts like modules, controllers, providers (services), and dependency injection.
    TypeScript-First:
    Embracing TypeScript provides strong typing, which enhances code quality, maintainability, and developer productivity, especially in large-scale applications.
    Built on Top of HTTP Frameworks:
    NestJS leverages robust HTTP server frameworks like Express by default, with the option to use Fastify for improved performance. It adds a layer of abstraction and structure on top of these foundations.
    Focus on Scalability and Maintainability:
    The framework's design principles, including modularity and well-defined architectural patterns, make it suitable for building applications that can easily scale and be maintained over time.
    Support for Microservices:
    NestJS provides native support for building microservices, offering features and patterns for inter-service communication and management.
    Enterprise-Ready:
    Its structured approach, strong typing, and support for various architectural patterns make NestJS a popular choice for enterprise-level applications, used by companies like Adidas and Roche.
---
"""
        
        # Generate article using LLM
        article_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert technical writer. Create a comprehensive, 
            engaging 250-word article about the given module using the provided assets as reference.
            
            The article should:
            - Be exactly around 250 words
            - Be informative and well-structured
            - Include key concepts and takeaways
            - Be suitable for learners
            - Have a clear introduction, body, and conclusion"""),
            ("human", f"""Module: NestJs course
            Description: NestJs Course
            
            Assets Information:
            {assets_context}
            
            Please write a 250-word article about this module.""")
        ])
        
        chain = article_prompt | self.llm
        article_content = chain.invoke({})
        return article_content
        # Save article to MongoDB
        article_doc = {
            "module_id": module_id,
            "module_title": module.get('title', 'Untitled'),
            "content": article_content.content,
            "word_count": len(article_content.content.split()),
            "created_at": datetime.utcnow(),
            "assets_used": [str(asset['_id']) for asset in assets]
        }
        
        result = self.articles_collection.insert_one(article_doc)
        article_ids.append(str(result.inserted_id))
        
        print(f"Generated article for module: {module.get('title', 'Untitled')}")
        
        return article_ids
    


    def process_video(self, yt_url, gdrive_url, module_name) -> List[str]:
        print("gdrive_url", gdrive_url)
        video_path = download_from_gdrive(gdrive_url, os.path.join(self.download_video_path, f"{module_name}.mp4"))
        transcript = fetch_and_clean_transcript(yt_url)
        print("transcript", transcript)
        print("video_path", video_path)
        if not video_path:
            print("Video not downloaded")
            return
        module_clips = []
        # Extract relevant timelines using LLM
        # Extract relevant timelines using LLM
        timeline_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert video editor. Analyze the transcript and identify 
the most important segment of less than 300 seconds that teach the core concepts of the module.

Return a JSON array of segments with start_time, end_time (in seconds), and reason.
Select only 1 most valuable segment that covers the module."""),
("human", f"""Module: {module_name}

Transcript: {transcript}

Please identify the most important teaching segments.""")
        ])
        
        class StartEndOutput(BaseModel):
            start_time: int = Field(description="Start of video in seconds")
            end_time: int = Field(description="End of video in seconds")

        class ClipOutput(BaseModel):
            output: List[StartEndOutput] = Field(description="List of segments of start_time and end_time")
        
        structured_llm = self.llm.with_structured_output(StartEndOutput)

        chain = timeline_prompt | structured_llm
        output_path = ""
        try:
            segment: StartEndOutput = chain.invoke({})
            print("segments", segment)
            # Extract video clips based on identified segments
            # for i, segment in enumerate(segments.output):
            start_time = segment.start_time
            end_time = segment.end_time
            
            # Create clip using moviepy
            try:
                video = VideoFileClip(video_path)
                clipped = video.subclip(start_time, end_time)
                output_path = os.path.join("./clipped_videos", f"{module_name}_highlights.mp4")
                # Write the result
                clipped.write_videofile(output_path, codec="libx264", audio_codec="aac")
            except Exception as e:
                print(f"Error processing video clip: {e}")
        
        except Exception as e:
            print(f"Error processing transcript: {e}")
        
        return output_path
    
    
    def get_top_engaging_modules(self, program_id: str) -> List[str]:
        """
        Fetch modules across all courses inside a program,
        and use LLM to pick 4 optimal module IDs based on title + description.
        """

        # fetch program
        program = self.db.find_one(self.collection_name, {"_id": ObjectId(program_id)})
        if not program:
            print(f"No program found with id {program_id}")
            return []

        # flatten modules across all courses
        modules = []
        for course in program.get("courses", []):
            for module in course.get("module", []):
                modules.append({
                    "id": str(module["_id"]),
                    "title": module.get("title", "Untitled"),
                    "description": module.get("description", "")[:300]  # preview
                })

        if not modules:
            print("No modules found in program.")
            return []

        # prepare modules for LLM
        modules_text = "\n".join([
            f"ID: {m['id']}, Title: {m['title']}, Description: {m['description']}"
            for m in modules
        ])

        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a helpful AI that selects the best learning modules based on title and description."),
            ("human", f"""
You are an expert learning content curator.

You are given a list of modules with their titles and short descriptions:

{modules_text}

Your task:
1. Analyse the **topic importance** from the title and description.
2. Prefer modules that cover **diverse topics** (avoid picking very similar ones).
3. Select modules that would be **most attractive and useful** for learners.
4. Return EXACTLY 4 module IDs.
""")
        ])

        # Pydantic model for structured output
        class ModuleSelectionOutput(BaseModel):
            module_ids: List[str] = Field(
                description="Exactly 4 selected module IDs that are most engaging and diverse"
            )

        structured_llm = self.llm.with_structured_output(ModuleSelectionOutput)
        chain = prompt | structured_llm

        try:
            result: ModuleSelectionOutput = chain.invoke({})
            return result.module_ids
        except Exception as e:
            print(f"Error selecting modules: {e}")
            return []