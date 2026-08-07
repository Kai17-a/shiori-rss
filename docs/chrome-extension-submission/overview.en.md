# Overview

## Short

This is the Chrome extension for Shiori Keeper. It saves the title and URL of the current page to a Shiori Keeper API server, lets you organize saved items with folders and tags, and supports checking whether the API server is reachable.

## Long

Shiori Keeper is a Chrome extension that lets you save the page you are currently viewing as a bookmark. It reads the current tab title and URL and sends them to a locally running Shiori Keeper API server.

When saving a bookmark, you can choose from folders and tags that are already managed in the app, which makes it easier to organize and find items later. The extension also includes an API connection check so you can confirm that the destination server is available before saving.

The extension stores the API server URL in `chrome.storage.local`, updates existing bookmarks by URL when possible, and falls back to creating a new bookmark when no match is found.

The extension is designed to be used together with the main Shiori Keeper app, and saved data is managed in Shiori Keeper's database.

Project page: https://github.com/Kai17-a/shiori-keeper
