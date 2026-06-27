return {
  {
    "stevearc/conform.nvim",
    -- event = 'BufWritePre', -- uncomment for format on save
    opts = require "configs.conform",
  },

  -- These are some examples, uncomment them if you want to see them work!
  {
    "neovim/nvim-lspconfig",
    config = function()
      require "configs.lspconfig"
    end,
  },

  -- test new blink
  -- { import = "nvchad.blink.lazyspec" },

  -- {
  -- 	"nvim-treesitter/nvim-treesitter",
  -- 	opts = {
  -- 		ensure_installed = {
  -- 			"vim", "lua", "vimdoc",
  --      "html", "css"
  -- 		},
  -- 	},
  -- },

  {
    "nvim-treesitter/nvim-treesitter",
    branch = "master",
    opts = function()
      return require "nvchad.configs.treesitter"
    end,
    config = function(_, opts)
      local query = require "vim.treesitter.query"
      local directive_opts = vim.fn.has "nvim-0.10" == 1 and { force = true, all = false } or true
      local aliases = {
        ex = "elixir",
        pl = "perl",
        sh = "bash",
        ts = "typescript",
        uxn = "uxntal",
      }
      local mimetypes = {
        ["application/ecmascript"] = "javascript",
        ["importmap"] = "json",
        ["module"] = "javascript",
        ["text/ecmascript"] = "javascript",
      }

      local function capture_node(match, capture_id)
        local node = match[capture_id]
        if type(node) == "table" then
          return node[1]
        end
        return node
      end

      query.add_directive("set-lang-from-info-string!", function(match, _, bufnr, pred, metadata)
        local node = capture_node(match, pred[2])
        if not node then
          return
        end

        local alias = vim.treesitter.get_node_text(node, bufnr):lower()
        metadata["injection.language"] = vim.filetype.match { filename = "a." .. alias } or aliases[alias] or alias
      end, directive_opts)

      query.add_directive("set-lang-from-mimetype!", function(match, _, bufnr, pred, metadata)
        local node = capture_node(match, pred[2])
        if not node then
          return
        end

        local value = vim.treesitter.get_node_text(node, bufnr)
        local parts = vim.split(value, "/", {})
        metadata["injection.language"] = mimetypes[value] or parts[#parts]
      end, directive_opts)

      query.add_directive("downcase!", function(match, _, bufnr, pred, metadata)
        local id = pred[2]
        local node = capture_node(match, id)
        if not node then
          return
        end

        metadata[id] = metadata[id] or {}
        metadata[id].text = string.lower(vim.treesitter.get_node_text(node, bufnr, { metadata = metadata[id] }) or "")
      end, directive_opts)

      require("nvim-treesitter.configs").setup(opts)
    end,
  },
}
