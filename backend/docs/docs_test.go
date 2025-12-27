package docs

import "testing"

func TestSwaggerInfoMetadata(t *testing.T) {
	if SwaggerInfo.Title == "" {
		t.Fatal("swagger info title should be populated")
	}
	if SwaggerInfo.BasePath == "" {
		t.Fatal("swagger base path should be set")
	}
}
