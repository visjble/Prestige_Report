import asyncio
import os
import re
from datetime import datetime
from typing import Dict, Any, List, Tuple
from anthropic import AsyncAnthropic

def load_api_key():
    try:
        # First try to get the key from environment variable (GitHub Secrets)
        api_key = os.environ.get("ANTHROPIC_KEY")
        
        # If environment variable is not set, fall back to file (for local development)
        if not api_key:
            try:
                with open("scripts/key.txt", "r") as file:
                    api_key = file.read().strip()
            except FileNotFoundError:
                print("Warning: Failed to load API key from file, and no environment variable found")
                
        if not api_key:
            raise ValueError("API key is empty")
            
        return api_key
    except Exception as e:
        print(f"Error reading API key: {e}")
        exit(1)
        
# Get API key at module level
API_KEY = load_api_key()

class Agent:
    def __init__(self, name: str, role: str, system_prompt: str):
        self.name = name
        self.role = role
        self.system_prompt = system_prompt
        self.client = AsyncAnthropic(api_key=API_KEY)

    async def analyze(self, prompt_content: str) -> Dict[str, Any]:
        try:
            response = await self.client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=1024,
                system=self.system_prompt,
                messages=[{"role": "user", "content": prompt_content}]
            )
            
            # Handle the response content properly
            content = response.content
            if isinstance(content, list):
                content = content[0].text if hasattr(content[0], 'text') else str(content[0])
            
            return {
                "agent": self.name,
                "response": content,
                "tokens": response.usage.input_tokens + response.usage.output_tokens
            }
        except Exception as e:
            return {
                "agent": self.name,
                "response": f"Analysis failed: {str(e)}",
                "tokens": 0
            }

class VanityFairEditor(Agent):
    def __init__(self):
        super().__init__(
            name="Vanity Fair Editor",
            role="Editor",
            system_prompt="You are a senior editor at an equivalent Vanity Fair magazine. Generate 2 captivating feature story ideas that blend celebrity profiles, cultural analysis, investigative reporting, and human interest. Each idea should be numbered and consist of a compelling title followed by a one-sentence description. Focus on topics that would appeal to Vanity Fair's sophisticated audience."
        )

class VanityFairWriter(Agent):
    def __init__(self):
        super().__init__(
            name="Vanity Fair Writer",
            role="Writer",
            system_prompt="You are an accomplished writer for an equivalent Vanity Fair magazine. Write a captivating 200-word story based on the assigned topic. Use Vanity Fair's signature blend of sophisticated prose, cultural insight, and narrative flair. Include a compelling headline."
        )

async def generate_feature_ideas():
    editor = VanityFairEditor()
    prompt = "Please generate 3 captivating feature ideas for the next issue of Vanity Fair."
    
    print("\nAsking editor for feature ideas...")
    result = await editor.analyze(prompt)
    
    print(f"\n📋 FEATURE IDEAS FROM {result['agent'].upper()}")
    print("=" * 50)
    print(result['response'].strip())
    
    return result['response'], result['tokens']

async def write_feature(ideas):
    writer = VanityFairWriter()
    
    # Parse the numbered list to extract ideas
    idea_lines = [line.strip() for line in ideas.split('\n') if line.strip()]
    idea_list = []
    
    # More robust idea extraction
    current_idea = ""
    current_number = None
    
    for line in idea_lines:
        # Check if line starts a new numbered idea
        if re.match(r'^\d+\.', line):
            # If we were collecting a previous idea, save it
            if current_number is not None and current_idea:
                idea_list.append((current_number, current_idea))
            
            # Start a new idea
            parts = line.split('.', 1)
            current_number = int(parts[0])
            current_idea = parts[1].strip()
        elif current_number is not None:
            # Continue collecting the current idea
            current_idea += " " + line
    
    # Add the last idea if there is one
    if current_number is not None and current_idea:
        idea_list.append((current_number, current_idea))
    
    if not idea_list:
        print("Error: Could not parse any ideas from the editor's response.")
        return None, 0, None
    
    # Create a dictionary mapping idea numbers to full idea text
    idea_dict = {num: text for num, text in idea_list}
    
    # Extract titles and descriptions for each idea
    parsed_ideas = {}
    for num, text in idea_list:
        # Look for quoted title
        title_match = re.search(r'"([^"]+)"', text)
        if title_match:
            title = title_match.group(1)
            # Description is everything after the title
            full_text = text
            description = re.sub(r'"[^"]+":\s*', '', text).strip()
            parsed_ideas[num] = {
                "title": title,
                "description": description,
                "full_text": full_text
            }
        else:
            # Try to handle cases where title might not be in quotes
            # Assume first sentence might be the title
            parts = text.split(":", 1)
            if len(parts) > 1:
                title = parts[0].strip()
                description = parts[1].strip()
                parsed_ideas[num] = {
                    "title": title,
                    "description": description,
                    "full_text": text
                }
    
    # Send all ideas to the writer and have them choose one based on their personality
    prompt = f"""Here are 3 feature ideas for Vanity Fair:

{ideas}

select the ONE idea, Then write a compelling 300-word feature based on your selected idea."""
    
    print("\nSending all ideas to writer for selection and story creation...")
    result = await writer.analyze(prompt)
    
    print(f"\n✍️ FEATURE FROM {result['agent'].upper()}")
    print("=" * 50)
    print(result['response'].strip())
    
    # Try to extract the idea number chosen by the writer
    response_text = result['response']
    idea_number_match = re.search(r"I(?:'ve)? (?:chose|choose|select|picked|am choosing) idea (?:number )?(\d+)", response_text, re.IGNORECASE)
    if not idea_number_match:
        idea_number_match = re.search(r"Idea (?:number )?(\d+):", response_text, re.IGNORECASE)
    
    idea_number = int(idea_number_match.group(1)) if idea_number_match else 1
    
    # Get the chosen idea information
    chosen_idea_info = parsed_ideas.get(idea_number, None)
    
    if chosen_idea_info:
        headline = chosen_idea_info["title"]
        description = chosen_idea_info["description"]
    else:
        # Fallback if we couldn't parse the chosen idea properly
        headline = f"Vanity Fair Feature: Idea {idea_number}"
        description = idea_dict.get(idea_number, "")
    
    return result['response'], result['tokens'], {
        "idea_number": idea_number,
        "headline": headline,
        "description": description,
        "chosen_idea": idea_dict.get(idea_number, "")
    }


# Update the save_to_website function to add the anchor and properly update links

# Update the save_to_website function to add the anchor and properly update links

# Update the save_to_website function to add the anchor and properly update links

def save_to_website(ideas, story, metadata):
    today = datetime.now()
    date_str = today.strftime("%Y%m%d")
    human_date = today.strftime("%B %d, %Y")
    
    # Create directories if they don't exist
    docs_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "docs")
    stories_path = os.path.join(docs_path, "stories")
    css_path = os.path.join(docs_path, "assets", "css")
    img_path = os.path.join(docs_path, "assets")
    
    os.makedirs(stories_path, exist_ok=True)
    os.makedirs(css_path, exist_ok=True)
    os.makedirs(img_path, exist_ok=True)
    
    # Get metadata
    headline = metadata["headline"]
    description = metadata["description"]
    
    # Create a filename using date and title
    # Remove any non-alphanumeric characters (except spaces and hyphens)
    cleaned_headline = re.sub(r'[^\w\s-]', '', headline.lower())
    # Replace spaces and consecutive hyphens with a single hyphen
    cleaned_headline = re.sub(r'[\s-]+', '-', cleaned_headline)
    # Limit length to 40 characters
    cleaned_headline = cleaned_headline[:40].strip('-')
    
    # Make sure we have a meaningful filename - don't allow generic names
    if cleaned_headline == "vanity-fair-feature-idea" or not cleaned_headline:
        # Try to extract a more meaningful name from the actual content
        story_lines = story.strip().split("\n")
        for line in story_lines[:20]:
            if len(line.strip()) > 15 and not line.startswith("I choose") and not line.startswith("Idea"):
                potential_title = re.sub(r'[^\w\s-]', '', line.lower())
                potential_title = re.sub(r'[\s-]+', '-', potential_title)
                if len(potential_title) > 10:
                    cleaned_headline = potential_title[:40].strip('-')
                    break
        
        # If still using generic name, try to use the chosen idea
        if cleaned_headline == "vanity-fair-feature-idea" or not cleaned_headline:
            if metadata["chosen_idea"]:
                idea_text = re.sub(r'^\d+\.\s*', '', metadata["chosen_idea"])
                cleaned_headline = re.sub(r'[^\w\s-]', '', idea_text.lower())
                cleaned_headline = re.sub(r'[\s-]+', '-', cleaned_headline)
                cleaned_headline = cleaned_headline[:40].strip('-')
    
    # Generate unique filename with date prefix to ensure correct ordering
    filename = f"{date_str}-{cleaned_headline}.html"
    
    # Ensure filename is unique by adding a suffix if needed
    counter = 1
    original_filename = filename
    while os.path.exists(os.path.join(stories_path, filename)):
        filename = f"{date_str}-{cleaned_headline}-{counter}.html"
        counter += 1
    
    # Print debug info about filename generation
    print(f"Generated filename from headline: '{headline}'")
    print(f"Cleaned headline for filename: '{cleaned_headline}'")
    print(f"Final filename: '{filename}'")
    
    # Read the template
    try:
        with open("scripts/story_template.html", "r") as f:
            template = f.read()
    except FileNotFoundError:
        try:
            # Try to read from the stories folder as a fallback
            with open("stories/story_template.html", "r") as f:
                template = f.read()
        except FileNotFoundError:
            print("Creating template file...")
            template = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{STORY_TITLE}}</title>
    <link rel="stylesheet" href="../assets/css/style.css">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700&family=Source+Sans+Pro:wght@300;400;600&display=swap" rel="stylesheet">
    <style>
        body {
            font-family: 'Source Sans Pro', sans-serif;
            line-height: 1.6;
            color: #333;
            margin: 0;
            padding: 0;
            background-color: #fff;
        }
        
        .container {
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
        }
        
        .header-content {
            display: flex;
            flex-direction: column;
            align-items: center;
            margin-bottom: 30px;
        }
        
        .header-logo {
            margin-bottom: 15px;
        }
        
        .logo {
            display: block;
        }
        
        .header-text {
            text-align: center;
        }
        
        .site-description {
            font-style: italic;
            font-size: 1.2rem;
            margin: 0;
            color: #555;
        }
        
        .story-container {
            max-width: 800px;
            margin: 0 auto;
        }
        
        .story-header {
            margin-bottom: 40px;
            text-align: center;
        }
        
        .story-headline {
            font-family: 'Playfair Display', serif;
            font-size: 2.8rem;
            margin-bottom: 20px;
            line-height: 1.2;
        }
        
        .story-meta {
            font-style: italic;
            color: #666;
            margin-bottom: 20px;
        }
        
        .story-description {
            font-size: 1.3rem;
            line-height: 1.6;
            font-style: italic;
            margin-bottom: 30px;
            color: #555;
        }
        
        .story-content {
            font-size: 1.2rem;
            line-height: 1.8;
        }
        
        .story-content p {
            margin-bottom: 1.5em;
        }
        
        .back-link {
            display: inline-block;
            margin-top: 40px;
            font-weight: 600;
            text-decoration: none;
            color: #000;
        }
        
        .back-link:hover {
            text-decoration: underline;
        }
        
        /* Smooth scrolling for anchor links */
        html {
            scroll-behavior: smooth;
        }
        
        /* Style for the continue-reading anchor */
        #continue-reading {
            scroll-margin-top: 20px;
        }
    </style>
</head>
<body>
    <header>
        <div class="container">
            <div class="header-content">
                <div class="header-logo">
                    <img src="../assets/logo_sm.png" alt="Prestige Report Logo" class="logo" width="250" height="auto">
                </div>
                <div class="header-text">
                    <p class="site-description">Exclusive Stories From The World's Elite</p>
                </div>
            </div>
        </div>
    </header>

    <main class="container">
        <article class="story-container">
            <header class="story-header">
                <h1 class="story-headline">{{STORY_TITLE}}</h1>
                <div class="story-meta">
                    <span class="story-date">{{STORY_DATE}}</span>
                </div>
                <div class="story-description">
                    {{STORY_DESCRIPTION}}...
                </div>
            </header>
            
            <div class="story-content">
                {{STORY_CONTENT}}
            </div>
            
            <a href="../index.html" class="back-link">← Back to all stories</a>
        </article>
    </main>
</body>
</html>"""
            # Save the template for future use
            os.makedirs("scripts", exist_ok=True)
            with open("scripts/story_template.html", "w") as f:
                f.write(template)
    
    # Format the story content to HTML paragraphs
    # More robust extraction of content
    story_text = story.strip()
    
    # First, strip away any metadata or choice indicators that might appear at the start
    # This includes lines that start with "I choose", "I've chosen", "I select", "I decided", "I am going with", etc.
    choice_pattern = r'^(I\s+(choose|chose|select|picked|am\s+choosing|am\s+going\s+with|decided\s+on|will\s+go\s+with)|Selected|Chosen|Idea\s+(\#|\d+))[^\n]*\n+'
    story_text = re.sub(choice_pattern, '', story_text, flags=re.IGNORECASE | re.MULTILINE)
    
    # Remove any title/headline that appears at the beginning (usually in # markdown or ALL CAPS)
    title_pattern = r'^(#\s+.*?\n+|[A-Z\s:]{10,}$\n+)'
    story_text = re.sub(title_pattern, '', story_text, flags=re.MULTILINE)
    
    # Break into lines and process paragraphs
    story_lines = story_text.split("\n")
    paragraph = ""
    paragraphs = []
    
    for line in story_lines:
        line = line.strip()
        if not line:
            if paragraph:
                paragraphs.append(paragraph)
                paragraph = ""
        else:
            # Skip any markdown formatting or headers
            if line.startswith('#') or line.startswith('---') or line.startswith('==='):
                continue
                
            # Skip any "Idea selection" lines that might appear in the middle
            if re.match(r'^(Based on|I will use|I have chosen)', line, re.IGNORECASE):
                continue
                
            if paragraph:
                paragraph += " " + line
            else:
                paragraph = line
    
    # Add any remaining paragraph
    if paragraph:
        paragraphs.append(paragraph)
        
    # Additional validation: if we have no paragraphs, something went wrong
    if not paragraphs:
        # Fall back to simple paragraph splitting
        paragraphs = [p.strip() for p in story_text.split("\n\n") if p.strip()]
    
    # Convert paragraphs to HTML with validation
    story_content = ""  # Initialize the variable
    
    if not paragraphs:
        story_content = "<p>No content available.</p>"
    else:
        # Add first paragraph normally
        story_content += f"<p>{paragraphs[0]}</p>\n"
        
        # Add the continue-reading anchor at the start of the second paragraph
        if len(paragraphs) > 1:
            story_content += f'<p id="continue-reading">{paragraphs[1]}</p>\n'
            
            # Add remaining paragraphs
            for p in paragraphs[2:]:
                story_content += f"<p>{p}</p>\n"
        else:
            # If only one paragraph, still add the continue-reading anchor
            # This ensures the link doesn't break if there's only one paragraph
            story_content = f'<p id="continue-reading">{paragraphs[0]}</p>\n'
    
    # Replace template placeholders
    story_page = template.replace("{{STORY_TITLE}}", headline)
    story_page = story_page.replace("{{STORY_DATE}}", human_date)
    story_page = story_page.replace("{{STORY_DESCRIPTION}}", description)
    story_page = story_page.replace("{{STORY_CONTENT}}", story_content)
    
    # Replace IDEA_NUMBER if it exists in the template
    if "{{IDEA_NUMBER}}" in story_page:
        story_page = story_page.replace("{{IDEA_NUMBER}}", str(metadata.get("idea_number", "1")))
    
    # Remove the footer if it exists
    story_page = re.sub(r'<footer>.*?</footer>', '', story_page, flags=re.DOTALL)
    
    # Save the story page
    story_path = os.path.join(stories_path, filename)
    with open(story_path, "w") as f:
        f.write(story_page)
    print(f"- File saved: {story_path}")
    
    # Save/update style.css
    style_css_path = os.path.join(css_path, "style.css")
    if not os.path.exists(style_css_path):
        style_template_path = os.path.join(os.path.dirname(__file__), "style.css")
        if os.path.exists(style_template_path):
            with open(style_template_path, "r") as src:
                with open(style_css_path, "w") as dst:
                    dst.write(src.read())
        else:
            print("Warning: style.css not found in scripts directory")
    
    # Now update the index.html
    index_path = os.path.join(docs_path, "index.html")
    try:
        with open(index_path, "r") as f:
            index_content = f.read()
    except FileNotFoundError:
        # If index doesn't exist, create it from scratch
        index_template_path = os.path.join(os.path.dirname(__file__), "index.html")
        with open(index_template_path, "r") as f:
            index_content = f.read()
    
    # Create the new story card for the featured section
    # Ensure the description isn't too long
    short_description = description
    if len(short_description) > 150:
        short_description = short_description[:147] + "..."
    
    featured_story = f"""
        <div class="story-card featured">
            <h2 class="story-title">{headline}</h2>
            <div class="story-meta">
                <span class="story-date">{human_date}</span>
            </div>
            <div class="story-excerpt">
                <p>{short_description}</p>
                <a href="stories/{filename}#continue-reading" class="read-more">Continue reading →</a>
            </div>
        </div>
"""
    
    # Create a story card for the archive
    story_card = f"""
                <div class="story-card">
                    <h3 class="story-title">{headline}</h3>
                    <div class="story-meta">
                        <span class="story-date">{human_date}</span>
                    </div>
                    <p class="story-excerpt">{description}...</p>
                    <a href="stories/{filename}#continue-reading" class="read-more">Continue reading →</a>
                </div>
"""
    
    # Update the index.html
    # Check if story-grid exists in the index
    if '<div class="story-grid">' not in index_content:
        # Add the story-archive section with the story-grid
        main_container_pattern = r'</section>\s*\s*</main>'
        replacement = '''</section>

    <section class="story-archive">
        <h2 class="section-title">Recent Stories</h2>
        <div class="story-grid">
        </div>
    </section>

</main>'''
        index_content = re.sub(main_container_pattern, replacement, index_content)
    
    # Replace the featured story - with better pattern matching
    featured_pattern = r'<div class="story-card featured">[\s\S]*?</div>\s*</div>'
    if re.search(featured_pattern, index_content):
        index_content = re.sub(featured_pattern, featured_story, index_content, flags=re.DOTALL)
    else:
        # If featured story section not found, insert it
        featured_section_pattern = r'<section class="featured-story">\s*'
        if re.search(featured_section_pattern, index_content):
            index_content = re.sub(featured_section_pattern, f'<section class="featured-story">\n{featured_story}\n', index_content)
        else:
            # If neither exists, add both
            main_pattern = r'<main class="container">\s*'
            featured_section = f'''<section class="featured-story">
{featured_story}
</section>'''
            index_content = re.sub(main_pattern, f'<main class="container">\n\n{featured_section}\n\n', index_content)
    
    # Add the new story to the archive - with better validation
    story_grid_pattern = r'<div class="story-grid">'
    if story_grid_pattern in index_content:
        index_content = re.sub(story_grid_pattern, f'<div class="story-grid">\n{story_card}', index_content)
    
    # Save the updated index
    with open(index_path, "w") as f:
        f.write(index_content)
    
    print(f"\n✅ Website updated successfully!")
    print(f"- New story: {headline}")
    print(f"- File saved: docs/stories/{filename}")
    
       
async def main():
    # Verify API key at startup
    try:
        test_client = AsyncAnthropic(api_key=API_KEY)
    except Exception as e:
        print(f"Error: Invalid API key configuration: {e}")
        return

    print("\n🌟 VANITY FAIR FEATURE GENERATOR 🌟")
    print("=" * 50)
    
    # Generate feature ideas
    ideas, editor_tokens = await generate_feature_ideas()
    
    # Automatically pass ideas to writer
    story, writer_tokens, metadata = await write_feature(ideas)
    
    if story:
        # Save to website
        save_to_website(ideas, story, metadata)
        
        # Print cost estimation
        total_tokens = editor_tokens + writer_tokens
        print(f"\n💰 Estimated API Cost: ${(total_tokens * 0.00015):.2f}")
        print("=" * 50)

if __name__ == "__main__":
    asyncio.run(main())