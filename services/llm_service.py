import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.output_parsers import JsonOutputParser
from langchain.prompts import ChatPromptTemplate
from services.db_service import DBService
from typing import List, Dict, Any
from bson import ObjectId
from moviepy.editor import VideoFileClip, concatenate_videoclips

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
    


    def process_videos(self, selected_modules: List[Dict[str, Any]]) -> List[str]:
        processed_video_paths = []
        
        for module in selected_modules:
            module_id = str(module['_id'])
            module_title = module.get('title', 'Untitled').replace(' ', '_').replace('/', '_')
            
            # Find video assets for this module
            video_assets = list(self.assets_collection.find({
                "module_id": module_id,
                "type": "video"
            }))
            
            if not video_assets:
                print(f"No video assets found for module {module_id}")
                continue
            
            module_clips = []
            
            for video_asset in video_assets:
                transcript = video_asset.get('transcript', '')
                video_path = video_asset.get('file_path', '')
                
                if not transcript or not video_path:
                    continue
                
                # Extract relevant timelines using LLM
                timeline_prompt = ChatPromptTemplate.from_messages([
                    ("system", """You are an expert video editor. Analyze the transcript and identify 
                    the most important segment of 2-3 minutes that teach the core concepts of the module.
                    
                    Return a JSON array of segments with start_time, end_time (in seconds), and reason.
                    Select only 1 most valuable segment of 3-4 minutes that feels most engaging according to module.
                    
                    Format: {"start_time": 30, "end_time": 120, "reason": "Explains core concept"}"""),
                    ("human", f"""Module: {module.get('title', 'Untitled')}
                    
                    Transcript: {transcript}
                    
                    Please identify the most important teaching segment.""")
                ])
                
                chain = timeline_prompt | self.llm | JsonOutputParser()
                try:
                    segment = chain.invoke({})
                    start_time = segment.get('start_time', 0)
                    end_time = segment.get('end_time', 30)
                    
                    # Create clip using moviepy
                    try:
                        video = VideoFileClip(video_path)
                        clip = video.subclip(start_time, end_time)
                        module_clips.append(clip)
                        video.close()
                    except Exception as e:
                        print(f"Error processing video clip: {e}")
                        continue
                
                except Exception as e:
                    print(f"Error processing transcript: {e}")
                    continue
            
            # Concatenate all clips for this module
            if module_clips:
                try:
                    final_video = concatenate_videoclips(module_clips)
                    output_path = os.path.join(config.VIDEO_OUTPUT_DIR, f"{module_title}_highlights.mp4")
                    final_video.write_videofile(output_path, codec='libx264', audio_codec='aac')
                    
                    # Close clips to free memory
                    for clip in module_clips:
                        clip.close()
                    final_video.close()
                    
                    processed_video_paths.append(output_path)
                    print(f"Created highlight video: {output_path}")
                    
                except Exception as e:
                    print(f"Error creating final video: {e}")
        
        return processed_video_paths