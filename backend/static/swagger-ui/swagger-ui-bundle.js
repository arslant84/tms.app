// Basic SwaggerUI implementation
window.SwaggerUIBundle = function(config) {
  const ui = {
    initOAuth: function() {
      console.log("OAuth initialization skipped in minimal implementation");
    },
    presets: [],
    plugins: []
  };
  
  // Create basic UI structure
  const container = document.getElementById(config.dom_id);
  
  // Create header
  const header = document.createElement('div');
  header.className = 'swagger-ui';
  header.innerHTML = `
    <div class="topbar">
      <div class="wrapper">
        <div class="topbar-wrapper">
          <div>
            <img height="30" src="https://swagger.io/swagger-ui/dist/favicon-32x32.png" alt="Swagger UI">
            <span>Swagger UI</span>
          </div>
        </div>
      </div>
    </div>
    <div class="wrapper">
      <section class="info">
        <div class="info__title-section">
          <h2 class="title">${config.spec.info.title || 'API Documentation'}</h2>
          <p>${config.spec.info.description || ''}</p>
          <p>Version: ${config.spec.info.version || 'N/A'}</p>
        </div>
      </section>
      <div id="swagger-ui-endpoints"></div>
    </div>
  `;
  container.appendChild(header);
  
  // Create endpoints section
  const endpointsContainer = document.getElementById('swagger-ui-endpoints');
  
  // Group endpoints by tag
  const pathsByTag = {};
  for (const path in config.spec.paths) {
    for (const method in config.spec.paths[path]) {
      const endpoint = config.spec.paths[path][method];
      const tag = endpoint.tags && endpoint.tags.length > 0 ? endpoint.tags[0] : 'default';
      
      if (!pathsByTag[tag]) {
        pathsByTag[tag] = [];
      }
      
      pathsByTag[tag].push({
        path,
        method,
        endpoint
      });
    }
  }
  
  // Create tag sections
  for (const tag in pathsByTag) {
    const tagSection = document.createElement('div');
    tagSection.className = 'opblock-tag-section';
    tagSection.innerHTML = `
      <h3 class="opblock-tag">${tag}</h3>
    `;
    
    // Create endpoint blocks
    pathsByTag[tag].forEach(({path, method, endpoint}) => {
      const methodColors = {
        get: '#61affe',
        post: '#49cc90',
        put: '#fca130',
        delete: '#f93e3e',
        patch: '#50e3c2',
        options: '#0d5aa7',
        head: '#9012fe'
      };
      
      const opblock = document.createElement('div');
      opblock.className = 'opblock';
      opblock.innerHTML = `
        <div class="opblock-summary">
          <span class="opblock-summary-method" style="background-color: ${methodColors[method] || '#000'}">${method.toUpperCase()}</span>
          <span class="opblock-summary-path">${path}</span>
          <div class="opblock-summary-description">${endpoint.summary || ''}</div>
        </div>
        <div class="opblock-description-wrapper">
          <div class="opblock-description">${endpoint.description || ''}</div>
        </div>
      `;
      
      tagSection.appendChild(opblock);
    });
    
    endpointsContainer.appendChild(tagSection);
  }
  
  return ui;
};
