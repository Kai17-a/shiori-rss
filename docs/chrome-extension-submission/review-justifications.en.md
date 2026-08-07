# Review Justifications

## Privacy

Shiori Keeper only uses the permissions required to provide its bookmark-saving and bookmark-management features.

The extension reads the current tab title and URL when the user saves a bookmark, stores the API server URL in `chrome.storage.local`, and uses bookmark-related access to check and manage existing saved items by URL. It does not collect browsing history, does not use the data for advertising or tracking, and does not share user data with third parties beyond sending bookmark data to the user's configured Shiori Keeper API server.

For Chrome Web Store review, this extension complies with the Chrome Web Store Developer Program Policies by limiting data access to the minimum needed for its core functionality.

## Single Purpose

Shiori Keeper has a single, clearly defined purpose: saving the page the user is currently viewing as a bookmark in the Shiori Keeper app, sending it to the Shiori Keeper server the user has set up, and managing that saved bookmark afterward.

Every feature in the extension supports that purpose:

- Capture the active tab title and URL
- Send bookmark data to the configured Shiori Keeper API server
- Store the API server URL in local extension storage
- Check the server connection before saving
- Read and update existing bookmarks by URL when needed

The extension does not include unrelated functionality and is not intended for general browsing, advertising, analytics, or background data collection.

## Permissions

Shiori Keeper's browser extension requires the following permissions so users can quickly save the page they are currently viewing as a bookmark and manage saved items consistently.

### `tabs`

This permission is needed to read information about the active tab.

From the extension popup, we read the active tab's `title` and `url` so the current page can be saved as a bookmark without requiring the user to copy the URL manually. This makes it possible to register the page they are currently viewing with one action.

### `storage`

This permission is needed to store extension settings for each user.

We use `chrome.storage.local` to keep the API server URL and related configuration so the extension remembers the user's settings after the browser is restarted. This avoids requiring the user to re-enter the same settings every time.

### `bookmarks`

This permission is needed to work with Chrome bookmarks.

Shiori Keeper supports checking and updating existing bookmarks and managing duplicates based on URL. The `bookmarks` permission allows the extension to read bookmark data in Chrome so saved links can be managed consistently.

### Additional Notes

The extension uses these permissions only for the features described above.
It does not use them for advertising, tracking, or collecting browsing history unrelated to the product's functionality.

## Host Permissions

Shiori Keeper requests host permissions so the extension can communicate with the Shiori Keeper API server selected by the user.

The extension sends bookmark data, checks whether the API server is reachable, loads folders and tags for organization, and updates or deletes bookmarks through the configured server. Because the server URL is user-configurable and the extension is intended to work with a self-hosted environment, it needs host access that can reach the API endpoint the user has set up themselves.

The permission is used only for these API requests and not for unrelated browsing or background network access.
