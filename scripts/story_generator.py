import asyncio
import os
import re
from datetime import datetime
from typing import Dict, Any, List, Tuple
from anthropic import AsyncAnthropic

def load_api_key():
    try:
        with open("/home/q/Documents/PythonProjects/chat/ra.txt", "r") as file:  #THIS FILE CONTAINS YOUR ANTHROPIC API KEY
            api_key = file.read().strip()
            if not api_key:
                raise ValueError("API key is empty")
            return api_key
    except FileNotFoundError:
        print("Error: key.txt not found")
        exit(1)
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
            system_prompt="You are a senior editor at Vanity Fair magazine. Generate 10 captivating feature story ideas that blend celebrity profiles, cultural analysis, investigative reporting, and human interest. Each idea should be numbered and consist of a compelling title followed by a one-sentence description. Focus on topics that would appeal to Vanity Fair's sophisticated audience."
        )

class VanityFairWriter(Agent):
    def __init__(self):
        super().__init__(
            name="Vanity Fair Writer",
            role="Writer",
            system_prompt="You are an accomplished writer for Vanity Fair magazine. Write a captivating 200-word story based on the assigned topic. Use Vanity Fair's signature blend of sophisticated prose, cultural insight, and narrative flair. Include a compelling headline."
        )

async def generate_feature_ideas():
    editor = VanityFairEditor()
    prompt = "Please generate 10 captivating feature ideas for the next issue of Vanity Fair."
    
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
    
    for line in idea_lines:
        if line[0].isdigit() and '.' in line[:3]:
            idea_list.append(line)
    
    if not idea_list:
        print("Error: Could not parse any ideas from the editor's response.")
        return None, 0, None
    
    # Send all ideas to the writer and have them choose one based on their personality
    prompt = f"""Here are 10 feature ideas for Vanity Fair:

{ideas}

As a Vanity Fair writer, please select the ONE idea that most inspires you based on your writing style and creative instincts. Then write a compelling 200-word feature based on your selected idea. Include believable anecdotes, plausible insider details, and verisimilitude that makes the story feel authentic. Use the signature Vanity Fair style of blending reported facts with rich narrative. Begin by indicating which idea number you've chosen."""
    
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
    
    idea_number = idea_number_match.group(1) if idea_number_match else "?"
    
    # Try to extract the headline
    headline_match = re.search(r"^#+ (.+)$", response_text, re.MULTILINE)
    if not headline_match:
        # Look for a line that might be a headline (capitalized words, no ending punctuation)
        lines = response_text.split("\n")
        for line in lines[:10]:  # Check first 10 lines only
            if line and line.strip() and len(line) > 20 and not line.strip().endswith(('.', '?', '!')):
                if sum(1 for c in line if c.isupper()) / len(line) > 0.3:  # At least 30% capitals
                    headline = line.strip()
                    break
        else:
            headline = f"Vanity Fair Feature: Idea {idea_number}"
    else:
        headline = headline_match.group(1)
    
    chosen_idea = next((idea for idea in idea_list if idea.startswith(f"{idea_number}.")), None)
    
    return result['response'], result['tokens'], {
        "idea_number": idea_number,
        "headline": headline,
        "chosen_idea": chosen_idea
    }

def save_to_website(ideas, story, metadata):
    today = datetime.now()
    date_str = today.strftime("%Y%m%d")
    human_date = today.strftime("%B %d, %Y")
    
    # Create directories if they don't exist
    os.makedirs("docs/stories", exist_ok=True)
    os.makedirs("docs/assets/css", exist_ok=True)
    
    # Generate a filename-friendly version of the headline
    headline = metadata["headline"]
    filename_base = re.sub(r'[^\w\s-]', '', headline.lower())
    filename_base = re.sub(r'[\s-]+', '-', filename_base)
    filename = f"{date_str}-{filename_base[:50]}.html"
    
    # Read the template
    try:
        with open("scripts/story_template.html", "r") as f:
            template = f.read()
    except FileNotFoundError:
        print("Creating template file...")
        template = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{STORY_TITLE}} | Prestige Report</title>
    <link rel="stylesheet" href="../assets/css/style.css">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700&family=Source+Sans+Pro:wght@300;400;600&display=swap" rel="stylesheet">
    <style>
        .story-container {
            max-width: 800px;
            margin: 0 auto;
        }
        
        .story-header {
            margin-bottom: 40px;
            text-align: center;
        }
        
        .story-headline {
            font-size: 2.8rem;
            margin-bottom: 20px;
            line-height: 1.2;
        }
        
        .story-meta {
            font-style: italic;
            color: #666;
            margin-bottom: 20px;
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
        }
    </style>
</head>
<body>
    <header>
        <div class="container">
            <h1 class="site-title">Prestige Report</h1>
            <p class="site-description">Exclusive Stories From The World's Elite</p>
        </div>
    </header>

    <main class="container">
        <article class="story-container">
            <header class="story-header">
                <h1 class="story-headline">{{STORY_TITLE}}</h1>
                <div class="story-meta">
                    <span class="story-date">{{STORY_DATE}}</span> | Idea #{{IDEA_NUMBER}}
                </div>
            </header>
            
            <div class="story-content">
                {{STORY_CONTENT}}
            </div>
            
            <a href="../index.html" class="back-link">← Back to all stories</a>
        </article>
    </main>

    <footer>
        <div class="container">
            <p>&copy; 2025 Prestige Report</p>
            <p>Exclusive Stories From The World's Elite</p>
        </div>
    </footer>
</body>
</html>"""
        # Save the template for future use
        os.makedirs("scripts", exist_ok=True)
        with open("scripts/story_template.html", "w") as f:
            f.write(template)
    
    # Format the story content to HTML paragraphs
    # Remove any potential headline or idea number reference from the beginning
    story_lines = story.strip().split("\n")
    content_start = 0
    for i, line in enumerate(story_lines):
        if i > 5:  # Only check first few lines
            break
        if line.startswith("I choose") or line.startswith("I've chosen") or line.startswith("Idea #"):
            content_start = i + 1
    
    # Process the actual content
    story_content = ""
    paragraph = ""
    for line in story_lines[content_start:]:
        line = line.strip()
        if not line:
            if paragraph:
                story_content += f"<p>{paragraph}</p>\n"
                paragraph = ""
        else:
            if line.startswith('#'):  # Skip markdown headings
                continue
            if paragraph:
                paragraph += " " + line
            else:
                paragraph = line
    
    # Add any remaining paragraph
    if paragraph:
        story_content += f"<p>{paragraph}</p>\n"
    
    # Replace template placeholders
    story_page = template.replace("{{STORY_TITLE}}", headline)
    story_page = story_page.replace("{{STORY_DATE}}", human_date)
    story_page = story_page.replace("{{IDEA_NUMBER}}", metadata["idea_number"])
    story_page = story_page.replace("{{STORY_CONTENT}}", story_content)
    
    # Save the story page
    with open(f"docs/stories/{filename}", "w") as f:
        f.write(story_page)
    
    # Save/update style.css
    if not os.path.exists("docs/assets/css/style.css"):
        with open("scripts/style.css", "r") as src:
            with open("docs/assets/css/style.css", "w") as dst:
                dst.write(src.read())
    
    # Now update the index.html
    try:
        with open("docs/index.html", "r") as f:
            index_content = f.read()
    except FileNotFoundError:
        # If index doesn't exist, create it from scratch
        with open("scripts/index.html", "r") as f:
            index_content = f.read()
    
    # Extract first paragraph for excerpt
    excerpt = ""
    content_parts = story_content.split("<p>")
    if len(content_parts) > 1:
        first_para = content_parts[1].split("</p>")[0]
        # Truncate to around 150 chars
        if len(first_para) > 150:
            excerpt = first_para[:147] + "..."
        else:
            excerpt = first_para
    
    # Create the new story card for the featured section
    featured_story = f"""
            <div class="story-card featured">
                <h2 class="story-title">{headline}</h2>
                <div class="story-meta">
                    <span class="story-date">{human_date}</span>
                </div>
                <div class="story-content">
                    {story_content}
                    <a href="stories/{filename}" class="read-more">Read the full story →</a>
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
                    <p class="story-excerpt">{excerpt}</p>
                    <a href="stories/{filename}" class="read-more">Read more →</a>
                </div>
    """
    
    # Update the index.html
    # Replace the featured story
    featured_pattern = r'<div class="story-card featured">.*?</div>\s*</div>'
    index_content = re.sub(featured_pattern, featured_story, index_content, flags=re.DOTALL)
    
    # Add the new story to the archive
    story_grid_pattern = r'<div class="story-grid">'
    index_content = re.sub(story_grid_pattern, f'<div class="story-grid">\n{story_card}', index_content)
    
    # Save the updated index
    with open("docs/index.html", "w") as f:
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
