"""
Export Module for Google Search Scraper
Provides functionality to export search results in various formats:
- Markdown
- Notion (requires API keys)
- HTML (for browser-based PDF printing)
"""
import os
import logging
import json
import markdown
from datetime import datetime
from notion_client import Client


def generate_html_content(search_query, results, include_summaries=True):
    """
    Generate HTML content for export
    
    Args:
        search_query (str): The original search query
        results (list): List of search result dictionaries
        include_summaries (bool): Whether to include summaries in the export
        
    Returns:
        str: The generated HTML content
    """
    # Generate timestamp
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    
    # Start HTML content
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Search Results for: {search_query}</title>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; max-width: 800px; margin: 0 auto; padding: 20px; }}
            h1 {{ color: #2c3e50; border-bottom: 1px solid #eee; padding-bottom: 10px; }}
            h2 {{ color: #3498db; margin-top: 20px; }}
            .result {{ margin-bottom: 30px; border-bottom: 1px solid #eee; padding-bottom: 20px; }}
            .result h3 {{ margin-bottom: 5px; color: #2980b9; }}
            .result a {{ color: #2980b9; text-decoration: none; }}
            .result a:hover {{ text-decoration: underline; }}
            .description {{ color: #7f8c8d; margin-bottom: 10px; }}
            .summary {{ background-color: #f9f9f9; padding: 15px; border-left: 4px solid #3498db; }}
            .timestamp {{ color: #95a5a6; font-style: italic; font-size: 0.9em; margin-top: 30px; }}
            .source {{ font-size: 0.8em; color: #7f8c8d; margin-top: 5px; }}
        </style>
    </head>
    <body>
        <h1>Search Results for: {search_query}</h1>
    """
    
    # Add each result
    for i, result in enumerate(results):
        html_content += f"""
        <div class="result">
            <h3><a href="{result['link']}" target="_blank">{result['title']}</a></h3>
            <div class="source">{result['link']}</div>
            <div class="description">{result['description']}</div>
        """
        
        # Add summary if available and requested
        if include_summaries and result.get('summary'):
            html_content += f"""
            <h4>Summary:</h4>
            <div class="summary">{result['summary']}</div>
            """
            
        html_content += "</div>"
    
    # End HTML content
    html_content += f"""
        <div class="timestamp">Generated on: {timestamp}</div>
        <div class="timestamp">Google Search Scraper Application</div>
    </body>
    </html>
    """
    
    return html_content


def export_to_pdf(search_query, results, include_summaries=True):
    """
    Export search results to PDF
    
    Args:
        search_query (str): The original search query
        results (list): List of search result dictionaries
        include_summaries (bool): Whether to include summaries in the export
        
    Returns:
        bytes: The PDF document as bytes
    """
    try:
        # Generate HTML content
        html_content = generate_html_content(search_query, results, include_summaries)
        
        # Convert HTML to PDF
        html = HTML(string=html_content)
        pdf_bytes = html.write_pdf()
        
        return pdf_bytes
        
    except Exception as e:
        logging.error(f"Error exporting to PDF: {str(e)}")
        raise


def export_to_markdown(search_query, results, include_summaries=True):
    """
    Export search results to Markdown
    
    Args:
        search_query (str): The original search query
        results (list): List of search result dictionaries
        include_summaries (bool): Whether to include summaries in the export
        
    Returns:
        str: The markdown content
    """
    try:
        # Generate timestamp
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        
        # Start markdown content
        md_content = f"# Search Results for: {search_query}\n\n"
        
        # Add each result
        for i, result in enumerate(results):
            md_content += f"## [{result['title']}]({result['link']})\n\n"
            md_content += f"Source: {result['link']}\n\n"
            md_content += f"{result['description']}\n\n"
            
            # Add summary if available and requested
            if include_summaries and result.get('summary'):
                md_content += f"### Summary:\n\n"
                md_content += f"> {result['summary']}\n\n"
            
            md_content += "---\n\n"
        
        # Add footer
        md_content += f"*Generated on: {timestamp}*\n\n"
        md_content += "*Google Search Scraper Application*"
        
        return md_content
        
    except Exception as e:
        logging.error(f"Error exporting to Markdown: {str(e)}")
        raise


def export_to_notion(search_query, results, notion_token, database_id, include_summaries=True):
    """
    Export search results to Notion
    
    Args:
        search_query (str): The original search query
        results (list): List of search result dictionaries
        notion_token (str): Notion API integration token
        database_id (str): Notion database ID
        include_summaries (bool): Whether to include summaries in the export
        
    Returns:
        dict: Response from Notion API
    """
    try:
        # Initialize Notion client
        notion = Client(auth=notion_token)
        
        # Keep track of created pages
        created_pages = []
        
        # Process each result
        for result in results:
            # Prepare summary content
            summary_content = result.get('summary', '') if include_summaries else ''
            
            # Create page in Notion database
            new_page = notion.pages.create(
                parent={"database_id": database_id},
                properties={
                    "Title": {
                        "title": [
                            {
                                "text": {
                                    "content": result['title']
                                }
                            }
                        ]
                    },
                    "URL": {
                        "url": result['link']
                    },
                    "Query": {
                        "rich_text": [
                            {
                                "text": {
                                    "content": search_query
                                }
                            }
                        ]
                    }
                },
                children=[
                    {
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [
                                {
                                    "type": "text",
                                    "text": {
                                        "content": result['description']
                                    }
                                }
                            ]
                        }
                    },
                    {
                        "object": "block",
                        "type": "heading_3",
                        "heading_3": {
                            "rich_text": [
                                {
                                    "type": "text",
                                    "text": {
                                        "content": "Summary"
                                    }
                                }
                            ]
                        }
                    },
                    {
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [
                                {
                                    "type": "text",
                                    "text": {
                                        "content": summary_content
                                    }
                                }
                            ]
                        }
                    }
                ]
            )
            
            created_pages.append(new_page)
            
        return {
            "success": True,
            "message": f"Exported {len(created_pages)} results to Notion",
            "pages": created_pages
        }
        
    except Exception as e:
        logging.error(f"Error exporting to Notion: {str(e)}")
        raise