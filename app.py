from flask import Flask, render_template, request, Response
import matplotlib
matplotlib.use('Agg')
import requests
import matplotlib.pyplot as plt
import io
import base64
from dotenv import load_dotenv
import os


app = Flask(__name__)


@app.route('/')
def index():
    return render_template('index.html')

# Fetches data from index.html (fetching user data from username)
@app.route('/fetch', methods=['POST'])
def fetch_github_data():
    github_username = request.form['username']
    load_dotenv()
    github_token = os.getenv('TOKEN')

    # GraphQL query to fetch user data with the 7 most recently updated repositories
    query = '''
    {
      user(login: "%s") {
        name
        login
        bio
        email
        avatarUrl
        createdAt
        repositories(first: 7, orderBy: {field: UPDATED_AT, direction: DESC}) {
          nodes {
            name
            description
          }
        }
      }
    }
    ''' % github_username
    
    # Display 10 Repos Heat Map
    commit_history_query = '''
    {
      user(login: "%s") {
        repositories(first: 10) {
          nodes {
            name
            defaultBranchRef {
              target {
                ... on Commit {
                  history {
                    nodes {
                      message
                      author {
                        name
                        email
                        date
                      }
                    }
                  }
                }
              }
            }
          }
        }
      }
    }
    ''' % github_username

# Displaying Top 2 Commits of the top 7 Repos
    user_commit_query = '''
{
  user(login: "%s") {
    repositories(first: 7, orderBy: {field: UPDATED_AT, direction: DESC}) {
      nodes {
        name
        defaultBranchRef {
          target {
            ... on Commit {
              history(first: 2) {
                nodes {
                  message
                  author {
                    name
                    email
                    date
                  }
                }
              }
            }
          }
        }
      }
    }
  }
}
''' % github_username


    

    # GraphQL API used
    graphql_url = 'https://api.github.com/graphql'


    headers = {
        'Authorization': 'Bearer ' + github_token,
    }

    # Make a request to GraphQL
    user_response = requests.post(graphql_url, json={'query': query}, headers=headers)
    commit_history = requests.post(graphql_url, json={'query': commit_history_query}, headers=headers)
    user_commit_response = requests.post(graphql_url, json={'query': user_commit_query}, headers=headers)


    if user_response.status_code == 200 and commit_history.status_code == 200 and user_commit_response.status_code == 200 :
        user_data = user_response.json()['data']['user']
        commit_history = commit_history.json()['data']['user']['repositories']['nodes']
        user_commits = user_commit_response.json()['data']['user']['repositories']['nodes']
        heatmap_data = generate_heatmap(commit_history)


        return render_template('user_info.html', user_data=user_data, commit_history=commit_history, heatmap_data=heatmap_data, user_commits=user_commits)
    
    else:
        error_message = "User not found. Please check the GitHub username."
        return render_template('index.html', error_message=error_message)
    
def generate_heatmap(commit_history):
    # Create an heatmap using Matplotlib
    fig, ax = plt.subplots(figsize=(8, 6))
    
    heatmap_data = [[len(repo['defaultBranchRef']['target']['history']['nodes']) for repo in commit_history]]
    im = ax.imshow(heatmap_data, cmap='coolwarm', aspect='auto')
    
    for i in range(len(commit_history)):
        for j in range(1):
            text = ax.text(i, j, heatmap_data[j][i], ha="center", va="center", color="black")
    

    cbar = ax.figure.colorbar(im, ax=ax, orientation='vertical')
    cbar.ax.set_ylabel('Number of Commits', rotation=-90, va="bottom")
    
    ax.set_xticks(range(len(commit_history)))
    ax.set_xticklabels([repo['name'] for repo in commit_history], rotation=90)
    ax.set_yticks([0])
    ax.set_yticklabels(['Commits'])
    ax.set_title('Commit History Heatmap')
    
    
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png')
    plt.close()
    
    # Encode the image as base64 
    heatmap_data = base64.b64encode(buffer.getvalue()).decode()
    return heatmap_data

@app.route('/heatmap')
def display_heatmap():
    heatmap_data = request.args.get('heatmap_data')

    # Decoding the data 
    return Response(base64.b64decode(heatmap_data), mimetype='image/png')

if __name__ == '__main__':
    app.run(debug=True)
