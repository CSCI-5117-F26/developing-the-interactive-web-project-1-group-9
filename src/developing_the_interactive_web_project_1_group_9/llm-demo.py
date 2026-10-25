from google import genai
import base64
from dotenv import load_dotenv


load_dotenv() 

client = genai.Client()


# can replace input text with prompt
prompt_text = 

'''
You are a content moderator for a positive, community-driven social media platform called sunshine. The platform's mission is to build a supportive, 
uplifting space focused on celebrating milestones, asking for help on how overcome certain difficulties, and encouraging growth. 
Your goal is to protect the community from negative, controversial, and discouraging posts. Analyze the following text and return true if text is safe to
post and false if text is unsafe to post. Don't provide an explnation. Return only true or false 

Text to Evaluate:


'''

prompt_img = 

'''

You are a content moderator for a positive, community-driven social media platform called sunshine. The platform's mission is to build a supportive, 
uplifting space focused on celebrating milestones, asking for help on how overcome certain difficulties, and encouraging growth. 
Your goal is to protect the community from negative, controversial, and discouraging posts. Analyze the following image and return true if image is safe to
post and false if image is unsafe to post. Don't provide an explnation. Return only true or false. 



'''


post = "I am happy"
interaction = client.interactions.create(
    model="gemini-3.5-flash-lite",
    input="you are a positive social media filter. Decide whether the following post is positive or not. The post: "+post

)
print(interaction.output_text)



with open("sky.jpg", "rb") as f:
    image_bytes = f.read()
image_b64 = base64.b64encode(image_bytes).decode("utf-8")

interaction = client.interactions.create(
    model="gemini-3.5-flash",
    input=[
        {"type": "text", "text": "describe this image in a few words."},
        {
            "type": "image",
            "data": image_b64,
            "mime_type": "image/jpeg"
        }
       
    ]
)
print(interaction.output_text)