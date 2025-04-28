import streamlit as st
import pandas as pd
import requests
import time
import os
import re
from io import BytesIO
from PIL import Image

# Set page configuration
st.set_page_config(
    page_title="AdGen AI Platform",
    page_icon="🎬",
    layout="wide"
)

# Initialize session state variables if they don't exist
if 'script' not in st.session_state:
    st.session_state.script = ""
if 'cleaned_summary' not in st.session_state:
    st.session_state.cleaned_summary = ""
if 'step' not in st.session_state:
    st.session_state.step = "start"
if 'replicas_df' not in st.session_state:
    st.session_state.replicas_df = None
if 'selected_replica' not in st.session_state:
    st.session_state.selected_replica = None

# API Keys (in a real app, these should be secured properly)
serper_api_key = "14b865cf1dae8d1149dea6a7d2c93f8ac0105970"
openai_api_key = "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"
groq_api_key = "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"
tavus_api_key = "d57e6c687a894213aa87abad7c1c5f56"
gemini_api_key = "AIzaSyBLzfjImenFp60acvXgKygaEDKGqKfHyKI"

# Set environment variables for API keys
os.environ["SERPER_API_KEY"] = serper_api_key
os.environ["OPENAI_API_KEY"] = openai_api_key
os.environ["GROQ_API_KEY"] = groq_api_key

# Default script for demonstration
default_script = (
    "Hey there... Are you feeling overwhelmed by credit card debt? I was too... until I found something that changed everything. "
    "I used to dread every bill that came in... It felt like a never-ending cycle of stress. "
    "But then I discovered this debt relief program that helped consolidate my payments into one simple monthly fee. "
    "The best part? It barely impacted my credit score! I finally started to breathe again, knowing there was a way out. "
    "If you're ready to take that first step towards relief, check it out now! You deserve to feel free from debt..."
)

# Helper functions
def clean_summary(text):
    lines = text.strip().split('\n')
    cleaned = ["Cleaned Campaign Summary:\n"]
    for line in lines:
        line = line.strip()
        # Skip unwanted lines
        if not line or line.startswith("✅") or line == "=" or "To be determined" in line or line == "END OF CHAT":
            continue
        cleaned.append(line)
    return "\n".join(cleaned)

def get_replicas():
    url = "https://tavusapi.com/v2/replicas"
    headers = {"x-api-key": tavus_api_key}
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            df = pd.json_normalize(data['data'])
            df_selected = df[['thumbnail_video_url', 'model_name', 'replica_id', 'replica_name']]
            return df_selected
        else:
            st.error(f"Error fetching replicas: {response.status_code} - {response.text}")
            return pd.DataFrame()
    except Exception as e:
        st.error(f"Exception while fetching replicas: {e}")
        return pd.DataFrame()

def generate_and_fetch_video(replica_id, video_name, script_text, audio_url=None, background_url=None):
    url = "https://tavusapi.com/v2/videos"
    headers = {
        "x-api-key": tavus_api_key,
        "Content-Type": "application/json"
    }

    payload = {
        "replica_id": replica_id,
        "script": script_text,
        "video_name": video_name
    }
    
    if audio_url:
        payload["audio_url"] = audio_url
    if background_url:
        payload["background_url"] = background_url

    try:
        with st.spinner("Creating video..."):
            creation_response = requests.post(url, json=payload, headers=headers)

        if creation_response.status_code != 200:
            return f"❌ Error creating video: {creation_response.status_code} - {creation_response.text}", None

        video_id = creation_response.json().get("video_id")
        if not video_id:
            return "❌ No video ID returned by Tavus.", None

        # Polling until status is 'ready'
        status_url = f"https://tavusapi.com/v2/videos/{video_id}"
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for i in range(20):  # Up to ~60 seconds
            progress_bar.progress((i+1)/20)
            status_text.text(f"Checking video status ({i+1}/20)...")
            
            time.sleep(3)
            status_response = requests.get(status_url, headers=headers)
            status_data = status_response.json()
            
            if status_data.get("status") == "ready":
                progress_bar.progress(1.0)
                stream_url = status_data.get("stream_url")
                return f"✅ Video is ready! Video ID: {video_id}", stream_url

        return "⏳ Video is still processing. Please check back later.", None
        
    except Exception as e:
        return f"❌ Exception during video generation: {str(e)}", None

# Mock function for CrewAI script generation
def generate_script_with_crewai(campaign_summary):
    # In a real implementation, this would call your CrewAI workflow
    # For now, we'll simulate the process with a delay and return the default script
    
    st.info("Generating script with CrewAI... (This may take a few minutes)")
    progress_bar = st.progress(0)
    
    # Simulate the CrewAI process with delay
    for i in range(10):
        progress_bar.progress((i+1)/10)
        time.sleep(1)  # Simulate work being done
    
    # In the real implementation, this would be the actual result from CrewAI
    script_result = {
        "hook": "Hey there... Are you feeling overwhelmed by credit card debt? I was too... until I found something that changed everything.",
        "body": "I used to dread every bill that came in... It felt like a never-ending cycle of stress. But then I discovered this debt relief program that helped consolidate my payments into one simple monthly fee. The best part? It barely impacted my credit score!",
        "cta": "If you're ready to take that first step towards relief, check it out now! You deserve to feel free from debt...",
        "final_script": default_script
    }
    
    return script_result

# UI Components
def render_start_page():
    st.title("🎬 AdGen AI Platform")
    st.subheader("Create compelling ad campaigns with AI")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Do you already have a script?")
        if st.button("Yes, I have a script", use_container_width=True):
            st.session_state.step = "edit_script"
            st.rerun()
    
    with col2:
        st.markdown("### Need to create a new script?")
        if st.button("No, help me create one", use_container_width=True):
            st.session_state.step = "briefer"
            st.rerun()

def render_briefer_page():
    st.title("🧠 Campaign Briefer")
    st.subheader("Let's gather information about your campaign")
    
    st.info("Chat with our AI assistant to create your campaign brief. The assistant will ask you questions about your campaign goals, target audience, and more.")
    
    # Simulate a conversation with the AI
    with st.form("briefer_form"):
        st.markdown("### Tell us about your campaign")
        campaign_goal = st.text_area("What is the goal of your campaign?", height=100)
        target_audience = st.text_area("Who is your target audience?", height=100)
        product_name = st.text_input("What is your product or service name?")
        key_benefits = st.text_area("What are the key benefits of your product/service?", height=100)
        preferred_style = st.selectbox("What style of ad do you prefer?", 
                                     ["Conversational", "Testimonial", "Educational", "Humorous", "Emotional"])
        
        submit_button = st.form_submit_button("Generate Campaign Brief")
        
        if submit_button:
            if not campaign_goal or not target_audience or not product_name or not key_benefits:
                st.error("Please fill out all fields")
            else:
                # Construct a summary from the form inputs
                summary = f"""
                Campaign Goal: {campaign_goal}
                Target Audience: {target_audience}
                Product/Service: {product_name}
                Key Benefits: {key_benefits}
                Preferred Style: {preferred_style}
                """
                
                st.session_state.cleaned_summary = clean_summary(summary)
                st.session_state.step = "generate_script"
                st.rerun()

def render_script_generation_page():
    st.title("📝 Script Generation")
    st.subheader("Creating your ad script with AI")
    
    st.markdown("### Campaign Brief Summary")
    st.info(st.session_state.cleaned_summary)
    
    if st.button("Generate Script with CrewAI"):
        # In a real implementation, this would call your CrewAI workflow
        script_result = generate_script_with_crewai(st.session_state.cleaned_summary)
        
        st.session_state.script = script_result["final_script"]
        st.session_state.step = "edit_script"
        st.rerun()

def render_script_editor_page():
    st.title("✏️ Script Editor")
    
    # If there's no script yet (coming directly from start page)
    if not st.session_state.script:
        st.session_state.script = default_script
    
    # Script editing section
    st.subheader("Edit Your Script")
    new_script = st.text_area("Script", st.session_state.script, height=300)
    
    if st.button("Save Script"):
        st.session_state.script = new_script
        st.success("Script saved!")
    
    # Section to choose next steps
    st.subheader("What would you like to do next?")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("Generate Audio", use_container_width=True):
            st.session_state.step = "audio_generation"
            st.rerun()
    
    with col2:
        if st.button("Generate Video", use_container_width=True):
            st.session_state.step = "video_generation"
            st.rerun()
    
    with col3:
        if st.button("Generate Images", use_container_width=True):
            st.session_state.step = "image_generation"
            st.rerun()

def render_audio_generation_page():
    st.title("🔊 Audio Generation")
    st.subheader("Generate voice audio for your ad")
    
    # Display the current script
    st.markdown("### Current Script")
    st.info(st.session_state.script)
    
    # ElevenLabs voice selection
    st.subheader("Select Voice")
    
    voices = {
        "Adam (Male, Professional)": "pNInz6obpgDQGcFmaJgB",
        "Alice (Female, Friendly)": "Xb7hH8MSUJpSbSDYk0k2",
        "Arnold (Male, Authoritative)": "VR6AewLTigWG4xSOukaG",
        "Aria (Female, Warm)": "9BWtsMINqrJLrRacOk9x",
        "Elli (Female, Young)": "MF3mGyEYCl7XYWbV9V6O",
        "Bill (Male, Casual)": "pqHfZKP75CvOlQylNhV4"
    }
    
    # Create columns for voice selection
    cols = st.columns(3)
    for i, (voice_name, voice_id) in enumerate(voices.items()):
        with cols[i % 3]:
            st.markdown(f"### {voice_name}")
            st.audio(f"https://via.placeholder.com/300x50.mp3?text={voice_name}", format="audio/mp3")
            if st.button(f"Select {voice_name.split()[0]}", key=f"voice_{voice_id}"):
                st.session_state.selected_voice = voice_id
                st.session_state.selected_voice_name = voice_name
                st.success(f"Selected voice: {voice_name}")
    
    # Generation options
    st.subheader("Generate Audio")
    
    with st.form("audio_generation_form"):
        if 'selected_voice' in st.session_state:
            st.info(f"Selected voice: {st.session_state.selected_voice_name}")
        else:
            st.warning("Please select a voice first")
        
        speed = st.slider("Speed", min_value=0.5, max_value=2.0, value=1.0, step=0.1)
        stability = st.slider("Stability", min_value=0.0, max_value=1.0, value=0.5, step=0.1)
        
        submit = st.form_submit_button("Generate Audio")
        
        if submit and 'selected_voice' in st.session_state:
            # Placeholder for actual API call
            st.success("Audio generation requested! In a real implementation, this would call the ElevenLabs API.")
            
            # Placeholder audio file (would be replaced with actual generated audio)
            st.audio("https://via.placeholder.com/300x50.mp3?text=Generated+Audio", format="audio/mp3")
    
    # Navigation buttons
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("Back to Script", use_container_width=True):
            st.session_state.step = "edit_script"
            st.rerun()
    
    with col2:
        if st.button("Generate Video", use_container_width=True):
            st.session_state.step = "video_generation"
            st.rerun()
    
    with col3:
        if st.button("Generate Images", use_container_width=True):
            st.session_state.step = "image_generation"
            st.rerun()

def render_video_generation_page():
    st.title("🎥 Video Generation")
    st.subheader("Create videos with AI avatars")
    
    # Display the current script
    st.markdown("### Current Script")
    st.info(st.session_state.script)
    
    # Choose video platform
    st.subheader("Select Video Platform")
    
    video_platform = st.radio(
        "Choose a platform:",
        ["Tavus", "HeyGen", "Veed.io"],
        horizontal=True
    )
    
    if video_platform == "Tavus":
        # Load Tavus replicas if not already loaded
        if st.session_state.replicas_df is None:
            with st.spinner("Loading Tavus models..."):
                st.session_state.replicas_df = get_replicas()
        
        if not st.session_state.replicas_df.empty:
            st.subheader("Select Tavus Replica")
            
            # Grid of replicas with thumbnails
            cols = st.columns(3)
            for i, (index, row) in enumerate(st.session_state.replicas_df.iterrows()):
                with cols[i % 3]:
                    st.markdown(f"### {row['replica_name']}")
                    st.video(row['thumbnail_video_url'])
                    if st.button(f"Select {row['replica_name']}", key=f"replica_{row['replica_id']}"):
                        st.session_state.selected_replica = {
                            'id': row['replica_id'],
                            'name': row['replica_name']
                        }
                        st.success(f"Selected replica: {row['replica_name']}")
            
            # Video generation form
            st.subheader("Generate Video")
            
            with st.form("video_generation_form"):
                if 'selected_replica' in st.session_state:
                    st.info(f"Selected replica: {st.session_state.selected_replica['name']}")
                else:
                    st.warning("Please select a replica first")
                
                video_name = st.text_input("Video Name", "My Ad Campaign")
                background_url = st.text_input("Background Video URL (optional)")
                audio_url = st.text_input("Audio URL (optional)")
                
                submit = st.form_submit_button("Generate Video")
                
                if submit and 'selected_replica' in st.session_state:
                    status_msg, video_url = generate_and_fetch_video(
                        st.session_state.selected_replica['id'],
                        video_name,
                        st.session_state.script,
                        audio_url,
                        background_url
                    )
                    
                    st.markdown(status_msg)
                    
                    if video_url:
                        st.video(video_url)
        else:
            st.error("Could not load Tavus replicas. Please check your API key or try again later.")
    
    elif video_platform == "HeyGen":
        st.info("HeyGen integration is coming soon!")
        
        # Placeholder UI for HeyGen
        st.subheader("HeyGen Models")
        cols = st.columns(3)
        for i in range(3):
            with cols[i]:
                st.markdown(f"### Model {i+1}")
                st.image("https://via.placeholder.com/150", caption=f"HeyGen Model {i+1}")
                st.button(f"Select Model {i+1}", key=f"heygen_model_{i}")
    
    elif video_platform == "Veed.io":
        st.info("Veed.io integration is coming soon!")
        
        # Placeholder UI for Veed.io
        st.subheader("Veed.io Templates")
        cols = st.columns(3)
        for i in range(3):
            with cols[i]:
                st.markdown(f"### Template {i+1}")
                st.image("https://via.placeholder.com/150", caption=f"Veed.io Template {i+1}")
                st.button(f"Select Template {i+1}", key=f"veed_template_{i}")
    
    # Navigation buttons
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("Back to Script", use_container_width=True):
            st.session_state.step = "edit_script"
            st.rerun()
    
    with col2:
        if st.button("Generate Audio", use_container_width=True):
            st.session_state.step = "audio_generation"
            st.rerun()
    
    with col3:
        if st.button("Generate Images", use_container_width=True):
            st.session_state.step = "image_generation"
            st.rerun()

def render_image_generation_page():
    st.title("🖼️ Image Generation")
    st.subheader("Create AI-generated images for your ad campaign")
    
    # Display the current script
    st.markdown("### Current Script")
    st.info(st.session_state.script)
    
    # Image prompt generation
    st.subheader("Generate Image Prompts")
    
    if st.button("Generate Prompts Based on Script"):
        # Simulate AI prompt generation (in real app, this would use your prompt_writer agent)
        with st.spinner("Generating image prompts..."):
            time.sleep(2)  # Simulating API call delay
            
            # These would be generated by your prompt_writer agent in a real implementation
            generated_prompts = [
                {
                    "id": "scene_1",
                    "prompt": "A person looking stressed while sorting through bills and credit card statements, dramatic lighting, shallow depth of field"
                },
                {
                    "id": "scene_2",
                    "prompt": "Close-up of a relaxed face with a relieved expression, soft natural lighting, symbolizing freedom from financial stress"
                },
                {
                    "id": "scene_3",
                    "prompt": "A clean, organized desk with a single bill and a calculator showing reduced numbers, representing financial organization"
                }
            ]
            
            st.session_state.image_prompts = generated_prompts
            st.success("Prompts generated successfully!")
    
    # Display generated prompts if available
    if 'image_prompts' in st.session_state:
        st.subheader("Generated Prompts")
        
        for i, prompt in enumerate(st.session_state.image_prompts):
            st.markdown(f"### Scene {i+1}")
            st.text_area(f"Prompt {i+1}", prompt["prompt"], key=f"prompt_{i}", height=100)
            
            if st.button(f"Generate Image for Scene {i+1}", key=f"gen_image_{i}"):
                # This would integrate with Gemini in a real implementation
                with st.spinner("Generating image..."):
                    time.sleep(3)  # Simulate API call
                    
                    # Placeholder image (would be replaced with actual generated image)
                    st.image("https://via.placeholder.com/512x512", caption=f"Generated image for Scene {i+1}")
                    st.download_button(
                        label=f"Download Image {i+1}",
                        data=BytesIO(b"placeholder"),  # Would be actual image data
                        file_name=f"scene_{i+1}.png",
                        mime="image/png"
                    )
    
    # Navigation buttons
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("Back to Script", use_container_width=True):
            st.session_state.step = "edit_script"
            st.rerun()
    
    with col2:
        if st.button("Generate Audio", use_container_width=True):
            st.session_state.step = "audio_generation"
            st.rerun()
    
    with col3:
        if st.button("Generate Video", use_container_width=True):
            st.session_state.step = "video_generation"
            st.rerun()

# Main app logic based on current step
if st.session_state.step == "start":
    render_start_page()
elif st.session_state.step == "briefer":
    render_briefer_page()
elif st.session_state.step == "generate_script":
    render_script_generation_page()
elif st.session_state.step == "edit_script":
    render_script_editor_page()
elif st.session_state.step == "audio_generation":
    render_audio_generation_page()
elif st.session_state.step == "video_generation":
    render_video_generation_page()
elif st.session_state.step == "image_generation":
    render_image_generation_page()

# Add footer
st.markdown("---")
st.markdown("#### AdGen AI Platform | Powered by CrewAI, Tavus, ElevenLabs, and Gemini")
