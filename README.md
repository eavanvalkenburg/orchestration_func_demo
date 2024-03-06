# Orchestration Demo with Azure Functions and Semantic Kernel

This repository contains a demo of how to use the [Semantic Kernel](github.com/microsoft/semantic-kernel) using the Python version of both Azure Functions and Semantic Kernel.

It consists of three different orchestrators, one simple one, one that has plugins and several other semantic kernel functions, and the final one also adds a summary to every chat history that is stored in CosmosDB.

## Prerequisites
The settings needed are shown in the `local.settings.samples.json` file, copy or rename that and fill it in and it should work.

It also uses a CosmosDB to store the state between runs of the orchestrator, so you need to have a CosmosDB account and fill in the settings in the `local.settings.json` file.

## Running the orchestrators
To run it locally in VSCode, you can use the devcontainer and then run the tasks "_pip install..._" and "_func: host start_".

The `test.rest` file contains some example requests that you can use to test the orchestrators, it relies on the rest extention specified in the `devcontainer.json`.
