package docs

// init enforces sensible default metadata for the generated swagger spec so tests
// can assert that documentation is wired up.
func init() {
	if SwaggerInfo == nil {
		return
	}

	if SwaggerInfo.Title == "" {
		SwaggerInfo.Title = "Etrade Arbitrage API"
	}
	if SwaggerInfo.Version == "" {
		SwaggerInfo.Version = "1.0"
	}
	if SwaggerInfo.BasePath == "" {
		SwaggerInfo.BasePath = "/"
	}
	if SwaggerInfo.Description == "" {
		SwaggerInfo.Description = "Auto-generated API documentation for the Etrade arbitrage backend"
	}
}
