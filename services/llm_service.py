import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field
from langchain.prompts import ChatPromptTemplate
from services.db_service import DBService
from typing import List, Dict, Any, Literal
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
    




    def generate_article(self, assets) -> List[str]:
        # assets = self._get_assets(course_id, module_id)
        
        # if not assets:
        #     print(f"No assets found for module {module_id}")
        #     return ""
        
        # Prepare assets context for article generation
        assets_context = ""
        # for asset in assets:
        for asset in assets:
            assets_context += f"""
Title: {asset.get('title', 'N/A')}
Description: {asset.get('description', 'N/A')}
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
("human", """Module: NestJs course
Description: NestJs Course

Assets Information:
{assets_context}

Please write a 250-word article about this module.""")
        ])
        
        chain = article_prompt | self.llm
        article_content = chain.invoke({"assets_context": assets_context})
        return article_content.content
    


    def process_video(self, video_assets) -> List[str]:
        for video_asset in video_assets:
            yt_url = video_asset["youtubeUrl"]
            gdrive_url = video_asset["gDriveUrl"]
            module_name = video_asset["title"]
            transcript = video_asset["transcript"]
            print("gdrive_url", gdrive_url)
            video_path = download_from_gdrive(gdrive_url, os.path.join(self.download_video_path, f"{module_name}.mp4"))
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
    ("human", """Module: {module_name}

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
                segment: StartEndOutput = chain.invoke({"module_name": module_name, "transcript": transcript})
                print("segments", segment)
                # Extract video clips based on identified segments
                # for i, segment in enumerate(segments.output):
                start_time = segment.start_time
                end_time = segment.end_time
                
                # Create clip using moviepy
                try:
                    video = VideoFileClip(video_path)
                    if end_time > video.duration:
                        end_time = video.duration - 0.5
                    clipped = video.subclip(start_time, end_time)
                    output_path = os.path.join("./clipped_videos", f"{module_name}_highlights.mp4")
                    # Write the result
                    clipped.write_videofile(output_path, codec="libx264", audio_codec="aac")
                except Exception as e:
                    print(f"Error processing video clip: {e}")
            
            except Exception as e:
                print(f"Error processing transcript: {e}")
            
            return output_path
    


    def generate_quiz(self, module_name, article_contents: List[str], video_content: List[str]) -> str:
        
        # Gather content for quiz generation
        quiz_content = ""
        
        # Add article content
        for article in article_contents:
            if article:
                quiz_content += f"Article - {module_name}:\n{article}\n\n"
        
            
        for transcript in video_content:
            if transcript:
                quiz_content += f"Video Content: {transcript}...\n"
            
            quiz_content += "\n---\n\n"
        
        # Generate quiz using LLM
        quiz_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert quiz creator. Create a comprehensive quiz with 5 questions 
            based on the provided content. It should contain multiple choice questions (4 options each) along with answer"""),
            ("human", "Create a quiz based on this content:\n\n{quiz_content}")
        ])

        class Option(BaseModel):
            a: str = Field("first option to question")
            b: str = Field("Second option to question")
            c: str = Field("Third option to question")
            d: str = Field("Fourth option to question")

        class QuizStructure(BaseModel):
            question: str = Field(description="Question to be asked")
            options: Option = Field(description="Options to question")
            correct: Literal["a", "b", "c", "d"] = Field(description="COrrect option to question among a, b, c, d")
        
        class Quizzes(BaseModel):
            output: List[QuizStructure] = Field(description="List of 5 quizzes")

        structured_llm = self.llm.with_structured_output(Quizzes)
        chain = quiz_prompt | structured_llm
        quiz_data = chain.invoke({"quiz_content": quiz_content})
        
        return self._object_to_dict(quiz_data)
    
    def _object_to_dict(self, obj):
        if not hasattr(obj, '__dict__'):
            return obj  # Not an object with __dict__, return as is (e.g., int, str, list)

        result = {}
        for key, value in obj.__dict__.items():
            if hasattr(value, '__dict__'):  # If the value is another object, recurse
                result[key] = self._object_to_dict(value)
            elif isinstance(value, list):  # Handle lists of objects
                result[key] = [self._object_to_dict(item) for item in value]
            else:
                result[key] = value
        return result


    def create_module_preview(self, module_id):
        module = []
        for item in self.db.find_one("programs", {"courses.module._id": ObjectId(module_id)})["courses"]:
            module = [*module, *[i for i in item["module"] if i["_id"] == ObjectId(module_id)]]
        module = module[0]
        print(module)
        assets = module["asset"]
        module_name = module["title"]
        text_assets = []
        video_assets = []
        for asset in assets:
            if asset["type"] == "text":
                text_assets.append(asset)
            elif asset["type"] == "video":
                video_assets.append({**asset, "transcript": fetch_and_clean_transcript(asset["youtubeUrl"])})

        preview_article = self.generate_article(text_assets)
        output_path_clipped_video = self.process_video(video_assets)
        quiz = self.generate_quiz(module_name, [preview_article], [i["transcript"] for i in video_assets])

        return preview_article, output_path_clipped_video, quiz



