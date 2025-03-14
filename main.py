import csv
import os
import sys
import argparse
from scraper import GitIngestScraper
from feature_analyzer import FeatureAnalyzer

def scrape_repositories(repo_data, output_dir):
    print("\n=== Phase 1: Scraping Repositories ===")
    successful_repos = []

    for repo, deployment in repo_data:
        print(f"\nScraping {repo}...")
        try:
            scraper = GitIngestScraper(repo)
            results = scraper.scrape()

            if not results:
                print(f"Failed to fetch data for {repo}")
                continue

            # Save scraped data
            base_filename = os.path.join(output_dir, repo.replace('/', '_'))
            with open(f'{base_filename}_directory_structure.txt', 'w', encoding='utf-8') as f:
                f.write(results['directory_structure'])
            with open(f'{base_filename}_code_content.txt', 'w', encoding='utf-8') as f:
                filtered_content = scraper.filter_css_content(results['textarea_content'])
                f.write(filtered_content)

            successful_repos.append((repo, deployment))
            print(f"Successfully scraped {repo}")

        except Exception as e:
            print(f"Error scraping {repo}: {str(e)}")
            continue

        finally:
            if 'scraper' in locals():
                del scraper  # Ensure browser is closed

    return successful_repos

def analyze_repositories(repo_data, output_dir):
    print("\n=== Phase 2: Analyzing Repositories ===")
    
    # Initialize CSV headers and analyzer
    infrastructure_features = [
        "already_deployed",
        "has_frontend",
        "has_cicd",
        "multiple_environments",
        "uses_containerization",
        "uses_iac",
        "high_availability"
    ] # Existing features
    code_features = [
        "authentication",
        "realtime_events",
        "storage",
        "caching",
        "ai_implementation",
        "database",
        "microservices",
        "monolith",
        "api_exposed",
        "message_queues",
        "background_jobs",
        "sensitive_data",
        "external_apis"
    ] # Existing features
    csv_headers = ["repository", "deployment", "framework"] + infrastructure_features + code_features
    
    csv_path = os.path.join(output_dir, "analysis_results.csv")
    with open(csv_path, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=csv_headers)
        writer.writeheader()
        
        analyzer = FeatureAnalyzer()
        for repo, _ in repo_data:  # Ignore the deployment value from repo_data
            print(f"\nAnalyzing {repo}...")
            try:
                base_filename = os.path.join(output_dir, repo.replace('/', '_'))
                
                # Read the saved files
                with open(f'{base_filename}_directory_structure.txt', 'r', encoding='utf-8') as f:
                    directory_structure = f.read()
                with open(f'{base_filename}_code_content.txt', 'r', encoding='utf-8') as f:
                    code_content = f.read()
                
                # Determine deployment platform
                deployment = analyzer.determine_deployment_platform(directory_structure, code_content, repo)
                
                # Create row data with detected deployment
                row_data = {
                    "repository": repo,
                    "deployment": deployment
                }
                
                # Rest of the analysis remains the same
                dir_results = analyzer.analyze_directory_structure(directory_structure)
                code_results = analyzer.analyze_with_llm(code_content)
                
                # Add features to row
                for feature in infrastructure_features:
                    row_data[feature] = 1 if dir_results.get(feature, False) else 0
                
                for feature in code_features:
                    row_data[feature] = 1 if code_results.get(feature, {}).get("present", False) else 0
                
                framework = analyzer.determine_framework(directory_structure, code_content)
                row_data["framework"] = framework
                
                writer.writerow(row_data)
                print(f"Added analysis results for {repo} (Detected deployment: {deployment})")
                
            except Exception as e:
                print(f"Error analyzing {repo}: {str(e)}")
                continue
    
    return csv_path

def process_repositories(input_file):
    output_dir = "temp"
    os.makedirs(output_dir, exist_ok=True)

    # Read repository names and deployment info from file
    repo_data = []
    with open(input_file, 'r') as f:
        for line in f:
            if line.strip():
                parts = line.strip().split('|')
                if len(parts) == 2:
                    repo = parts[0].strip()
                    deployment = parts[1].strip()
                    repo_data.append((repo, deployment))  # Store both repo and deployment

    # Phase 1: Scrape all repositories
    successful_repos = scrape_repositories(repo_data, output_dir)
    print(f"\nSuccessfully scraped {len(successful_repos)} out of {len(repo_data)} repositories")

    # Phase 2: Analyze all repositories
    if successful_repos:
        csv_path = analyze_repositories(successful_repos, output_dir)
        print(f"\nAnalysis complete! Results saved to {csv_path}")
    else:
        print("\nNo repositories were successfully scraped. Analysis cancelled.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Analyze multiple repositories and generate CSV report')
    parser.add_argument('input_file', help='Text file containing owner/repo entries, one per line')
    args = parser.parse_args()

    if not os.path.exists(args.input_file):
        print(f"Error: Input file '{args.input_file}' not found")
        sys.exit(1)

    process_repositories(args.input_file)
