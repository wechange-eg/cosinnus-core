# Frontend Redesign Prototype

1. Dotfile

Copy .env.dist to .env and configure settings:
- BASE_URL: The base URL of the platform, e.g. https://staging.wechange.de
- API_URL: The absolute API path of the platform, e.g. https://staging.wechange.de/api/v2
- USER_EMAIL and USER_PASSWORD: Initial data for the login form for convenience

2. Install requirements

`npm install`

3. Run development server

`npm run start`

4. Available scripts

- `npm run format` Format code using eslint and prettier
- `npm run lint` Lint check code using eslint, prettier and tsc
- `npm run build` Build package (into `/dist` folder)
- `npm run watch` Build package, watch for file changes
- `npm run start` Start dev server
- `npm run makemessages` Create translation template file under `/locale/messages.pot`
