package docs

import (
	"testing"

	"github.com/stretchr/testify/require"
	"github.com/swaggo/swag"
)

func TestSwaggerInfoMetadata(t *testing.T) {
	doc, err := swag.ReadDoc(SwaggerInfo.InstanceName())
	require.NoError(t, err)
	require.Contains(t, doc, "\"swagger\": \"2.0\"")
	require.Contains(t, doc, "\"/tasks\"")
}

func TestSwaggerInfoCustomization(t *testing.T) {
	original := SwaggerInfo.Title
	SwaggerInfo.Title = "Coverage Title"
	t.Cleanup(func() {
		SwaggerInfo.Title = original
	})

	doc, err := swag.ReadDoc(SwaggerInfo.InstanceName())
	require.NoError(t, err)
	require.Contains(t, doc, "Coverage Title")
}
