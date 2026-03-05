require("nvchad.configs.lspconfig").defaults()

local servers = { "html", "cssls", "pyright", "clangd" }
vim.lsp.enable(servers)


-- 2. SETUP CUSTOM SERVERS (Rust)
-- The README says: "Use vim.lsp.config('…') to customize or define a config."
vim.lsp.config('rust_analyzer', {
  settings = {
    ['rust-analyzer'] = {
      cargo = {
        allFeatures = true,
      },
    },
  },
})

-- After configuring, we must explicitly enable it.
vim.lsp.enable('rust_analyzer')
