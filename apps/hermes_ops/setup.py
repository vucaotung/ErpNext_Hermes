from setuptools import setup, find_packages

with open("requirements.txt") as f:
    # frappe itself is deliberately not listed here: it's the framework this
    # app installs into, always already present in the bench. Declaring it
    # as a normal dependency makes uv (bench's installer since frappe v15)
    # try to re-resolve frappe's own dependency tree — which fails because
    # frappe's pyproject.toml pins gunicorn via a git URL, and uv rejects
    # URL dependencies pulled in transitively. Any *genuinely external*
    # PyPI package hermes_ops needs should be added here instead.
    install_requires = [line.strip() for line in f if line.strip()]

setup(
    name="hermes_ops",
    version="0.1.0",
    description="ERPNext data model and permission scaffolding for the Hermes Agent / Telegram integration.",
    author="Company",
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    install_requires=install_requires,
)
