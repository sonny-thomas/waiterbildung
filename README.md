# TrustleOrg POC Scraper

## Table of Contents

- [TrustleOrg POC Scraper](#trustleorg-poc-scraper)
  - [Table of Contents](#table-of-contents)
  - [Introduction](#introduction)
  - [Features](#features)
  - [Installation](#installation)
  - [Usage](#usage)
  - [Configuration](#configuration)
  - [API Documentation](#api-documentation)
  - [Contributing](#contributing)
  - [License](#license)
  - [Contact](#contact)

## Introduction

The TrustleOrg POC Scraper is a web scraping application designed to extract and process course content from universities across the world. This tool is intended for developers and data analysts who need to gather educational information from web pages efficiently.

## Features

- **Efficient Web Scraping**: Extract course data from multiple university websites with ease.
- **Customizable**: Easily configure scraping rules and targets.
- **Data Processing**: Built-in tools for cleaning and processing scraped data.
- **Logging**: Comprehensive logging for monitoring scraping activities.
- **Error Handling**: Robust error handling to manage unexpected issues.

## Installation

To install the TrustleOrg POC Scraper, follow these steps:

1. **Clone the repository:**

   ```bash
   git clone https://github.com/TrustleOrg/poc-scraper.git
   cd poc-scraper
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

## Usage

To use the scraper, run the following command:

```bash
docker compose up -d
```

Ensure that all environment variables are set in the `.env` file before starting the application.

## Configuration

The `.env` file contains all the necessary configurations for the scraper.

## API Documentation

You can find the entire API documentation at the following endpoints:

- `/api/v1/docs`
- `/api/v1/redoc`

## Contributing

We welcome contributions from the community. To contribute, please follow these steps:

1. Fork the repository.
2. Create a new branch (`git checkout -b feat/your-feature-name`).
3. Make your changes.
4. Commit your changes following conventional commits (`git commit -m 'feat: add new feature'`).
5. Push to the branch (`git push origin feat/your-feature-name`).
6. Create a new Pull Request.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Contact

For any questions or inquiries, please contact us at [support@trustleorg.one](mailto:support@trustleorg.one).
