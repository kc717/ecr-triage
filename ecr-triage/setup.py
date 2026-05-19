from setuptools import setup, find_packages

setup(
    name="ecr-triage",
    version="0.1.0",
    description="LLM-assisted electronic case report prioritization using FHIR",
    author="Kevin Chen",
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=[
        "fhirpy>=1.4.0",
        "anthropic>=0.30.0",
        "pandas>=2.1.0",
        "python-dotenv>=1.0.0",
        "pyyaml>=6.0.0",
    ],
)
