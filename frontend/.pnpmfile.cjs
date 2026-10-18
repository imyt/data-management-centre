// hey-api calls the TypeScript JS API, which TypeScript 7 no longer ships. Give it its own
// TypeScript 6 instead of the app's TypeScript 7. Delete this file once hey-api supports 7.
module.exports = {
  hooks: {
    readPackage(pkg) {
      if (pkg.name === "@hey-api/openapi-ts") {
        delete pkg.peerDependencies?.typescript
        pkg.dependencies = { ...pkg.dependencies, typescript: "~6.0.2" }
      }
      return pkg
    },
  },
}
