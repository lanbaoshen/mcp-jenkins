# Contribution
Welcome contributions from the community!

Whether you're fixing bugs, adding new features, or improving documentation, your help is appreciated.

Please follow these guidelines to ensure a smooth contribution process:

1. Fork the Repository: Start by forking the repository to your own GitHub account.  
2. Create a Branch: Create a new branch for your feature or bug fix. Use a descriptive name for the branch.  
3. Make Changes: Implement your changes in the new branch. Ensure your code follows the project's coding style and conventions.  
4. Test Your Changes: Write tests for your changes and ensure all existing.  
5. Commit Changes: Commit your changes with clear and concise commit messages. Reference any related issues in your commit messages.  
6. Push Changes: Push your changes to your forked repository on GitHub.  
7. Open a Pull Request: Navigate to the original repository and open a pull request from your forked repository. Provide a detailed description of your changes and the problem they solve.  

You can install local development dependencies and pre-commit hooks:
```shell
pip install uv

uv sync --all-groups

git config commit.template .gitmessage.txt

# UT and ruff pre-commit hooks
pre-commit install

# You can also run pre-commit checks and tests manually:
pre-commit run --all-files
uv run pytest --cov=src
```
