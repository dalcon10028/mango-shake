# Gemini Code Understanding

## Project Overview

This project, "Mango Shake," is a Python application designed for cryptocurrency trading on the Bitget exchange. It appears to be a trading bot that connects to Bitget's public WebSocket API to receive real-time market data (candlesticks) and implements trading strategies. The initial strategy implemented is named "Squirrel."

The application is built using modern Python libraries, featuring asynchronous operations, reactive programming patterns, and dependency injection for a modular and maintainable codebase.

## Key Technologies

*   **Python 3:** The core programming language.
*   **`asyncio`:** Used for managing asynchronous operations, particularly for network I/O with the Bitget API and WebSockets.
*   **`reactivex`:** Implements the Observer pattern for handling real-time data streams from the WebSocket.
*   **`dependency-injector`:** Provides Inversion of Control (IoC) to manage dependencies between different components of the application, such as clients and strategies.
*   **Bitget API:** The application interacts with both the REST and WebSocket APIs of the Bitget cryptocurrency exchange.

## Project Structure

The project is organized into several key directories and files:

*   `src/app.py`: The main entry point of the application. It initializes the dependency injection container, establishes a connection to the Bitget WebSocket, and manages the main application lifecycle.
*   `src/config.yml`: A configuration file that stores settings for the Bitget API (URLs, product types) and parameters for the trading strategies (e.g., time intervals, trading pairs).
*   `src/bitget/`: This package contains all the components related to interacting with the Bitget exchange.
    *   `future_market_client.py`: A client for making requests to the Bitget Futures Market REST API.
    *   `websocket_public_client.py`: A client for connecting to and managing the public WebSocket stream from Bitget.
    *   `stream_manager.py`: Manages subscriptions to various data streams from the WebSocket.
*   `src/strategy/`: This package is intended to hold the different trading strategies.
    *   `squirrel_strategy_engine.py`: The first trading strategy, named "Squirrel." It is designed to process candle data streams.
*   `src/shared/`: This package contains utility components that are used across the application.
    *   `containers.py`: Defines the dependency injection container, wiring together the various components of the application.
    *   `tracing_client_session.py`: A wrapper around aiohttp's ClientSession to add tracing or other cross-cutting concerns.

## How to Run


Once you are inside the Poetry shell, the application can be started by running the main application file:

```bash
poetry shell
```

The application can be started by running the main application file:

```bash
python src/app.py
```

Before running, ensure that all the required dependencies listed in `pyproject.toml` are installed.

## Configuration

The application's behavior is configured through `src/config.yml`. This file allows you to set:

*   **Bitget API details:** Base URLs for the REST and WebSocket APIs.
*   **Strategy parameters:**
    *   `inst_type`: The type of instrument to trade (e.g., 'SUSDT-FUTURES').
    *   `intervals`: The time intervals for the candlestick data (e.g., '5m').
    *   `universe`: The list of trading pairs to monitor (e.g., 'BTCUSDT').
