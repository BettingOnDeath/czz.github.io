#!/usr/bin/env python3
"""
Enhanced build script that:
1. Converts Obsidian markdown to standard markdown
2. Organizes images by blog post
3. Automatically generates blog metadata
4. Copies everything to docs folder
"""

import os
import re
import json
import shutil
from pathlib import Path
from datetime import datetime

# Directories
BLOGS_DIR = Path('blogs')
DOCS_DIR = Path('docs')
DOCS_BLOGS_DIR = DOCS_DIR / 'blogs'
DOCS_ASSETS_DIR = DOCS_BLOGS_DIR / 'assets'
DOCS_JS_DIR = DOCS_DIR / 'js'

def extract_title_from_markdown(content):
    """Extract title from markdown content (first line or first heading)"""
    lines = content.strip().split('\n')
    if not lines:
        return None

    first_line = lines[0].strip()

    # Check if first line is a heading
    if first_line.startswith('#'):
        return first_line.lstrip('#').strip()

    # Otherwise use first non-empty line as title
    for line in lines:
        line = line.strip()
        if line and not line.startswith('![[') and not line.startswith('!['):
            return line[:50]  # Limit to 50 chars

    return None

def parse_date_from_filename(filename):
    """Parse date from filename (YYMMDD format)"""
    # Try to extract YYMMDD pattern
    match = re.match(r'(\d{2})(\d{2})(\d{2})', filename)
    if match:
        yy, mm, dd = match.groups()
        # Assume 20xx for years
        year = f"20{yy}"
        return f"{year}-{mm}-{dd}"

    return None

def extract_images_from_markdown(content):
    """Extract image filenames from markdown content"""
    # Match both Obsidian syntax ![[image.jpg]] and standard ![](image.jpg)
    obsidian_pattern = r'!\[\[([^\]]+)\]\]'
    standard_pattern = r'!\[.*?\]\((?:assets/)?([^\)]+)\)'

    images = []
    images.extend(re.findall(obsidian_pattern, content))
    images.extend(re.findall(standard_pattern, content))

    return images

def convert_obsidian_images(markdown, post_id):
    """Convert Obsidian image syntax to standard markdown with post-specific paths"""
    # Convert ![[image.jpg]] to ![](assets/POST_ID/image.jpg)
    return re.sub(
        r'!\[\[([^\]]+)\]\]',
        f'![](assets/{post_id}/\\1)',
        markdown
    )

def process_markdown_files():
    """Process all markdown files and generate metadata"""
    # Create docs/blogs directory if it doesn't exist
    DOCS_BLOGS_DIR.mkdir(parents=True, exist_ok=True)

    posts_metadata = []

    # Process each markdown file
    for md_file in sorted(BLOGS_DIR.glob('*.md'), reverse=True):
        print(f'Processing {md_file.name}...')

        # Read original content
        with open(md_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # Extract metadata
        post_id = md_file.stem  # filename without extension
        title = extract_title_from_markdown(content)
        date = parse_date_from_filename(md_file.stem)
        images = extract_images_from_markdown(content)

        # Convert Obsidian syntax
        converted_content = convert_obsidian_images(content, post_id)

        # Write to docs/blogs
        output_file = DOCS_BLOGS_DIR / md_file.name
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(converted_content)

        print(f'  [OK] Converted to {output_file}')
        try:
            print(f'  [OK] Title: {title}')
        except UnicodeEncodeError:
            print(f'  [OK] Title: [Contains non-ASCII characters]')
        print(f'  [OK] Date: {date}')
        print(f'  [OK] Images: {len(images)}')

        # Add to metadata
        if date and title:
            posts_metadata.append({
                'id': post_id,
                'date': date,
                'title': title,
                'images': images
            })

    return posts_metadata

def organize_assets(posts_metadata):
    """Organize assets by blog post"""
    source_assets = BLOGS_DIR / 'assets'

    if not source_assets.exists():
        print('No assets folder found')
        return

    # Remove existing assets folder in docs
    if DOCS_ASSETS_DIR.exists():
        shutil.rmtree(DOCS_ASSETS_DIR)

    DOCS_ASSETS_DIR.mkdir(parents=True, exist_ok=True)

    # Create subdirectories for each post and copy images
    for post in posts_metadata:
        post_id = post['id']
        images = post['images']

        if not images:
            continue

        # Create post-specific directory
        post_assets_dir = DOCS_ASSETS_DIR / post_id
        post_assets_dir.mkdir(exist_ok=True)

        # Copy images for this post
        for image in images:
            # Search for image in source assets (any subdirectory)
            found = False
            for root, dirs, files in os.walk(source_assets):
                if image in files:
                    source_file = Path(root) / image
                    dest_file = post_assets_dir / image
                    shutil.copy2(source_file, dest_file)
                    print(f'  Copied {image} to {post_id}/')
                    found = True
                    break

            if not found:
                print(f'  Warning: Image {image} not found for post {post_id}')

def update_blog_js(posts_metadata):
    """Update blog.js with generated metadata"""
    blog_js_path = DOCS_JS_DIR / 'blog.js'

    if not blog_js_path.exists():
        print('Warning: blog.js not found')
        return

    # Read current blog.js
    with open(blog_js_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Generate metadata JavaScript
    metadata_js = "postsMetadata: [\n"
    for post in posts_metadata:
        # Escape single quotes in title
        title = post['title'].replace("'", "\\'")
        metadata_js += f"    {{ id: '{post['id']}', date: '{post['date']}', title: '{title}', images: {json.dumps(post['images'])} }},\n"
    metadata_js += "  ]"

    # Replace postsMetadata array - use DOTALL flag to match across lines
    pattern = r'postsMetadata:\s*\[[\s\S]*?\]'
    new_content = re.sub(pattern, metadata_js, content, count=1, flags=re.DOTALL)

    # Write back
    with open(blog_js_path, 'w', encoding='utf-8') as f:
        f.write(new_content)

    print(f'\nUpdated {blog_js_path} with {len(posts_metadata)} posts')

def main():
    print('=' * 60)
    print('Enhanced Blog Build Process')
    print('=' * 60)

    # Process markdown files and extract metadata
    print('\n1. Processing markdown files...')
    posts_metadata = process_markdown_files()

    # Organize assets by post
    print('\n2. Organizing assets...')
    organize_assets(posts_metadata)

    # Update blog.js with metadata
    print('\n3. Updating blog.js...')
    update_blog_js(posts_metadata)

    print('\n' + '=' * 60)
    print('Build complete!')
    print(f'Processed {len(posts_metadata)} blog posts')
    print('Your blog is ready to deploy from the /docs folder')
    print('=' * 60)

if __name__ == '__main__':
    main()
