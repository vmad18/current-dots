require "nvchad.mappings"

local map = vim.keymap.set

-- === General ===
map("n", ";", ":", { desc = "CMD enter command mode", nowait = true })

-- === Disable old mappings ===
-- vim.keymap.del("n", "<C-0>")
-- vim.keymap.del("n", "<S-1>")
-- vim.keymap.del("n", "<S-2>")

-- === Custom abc mappings ===
map("n", "<C-1>", "<Home>", { desc = "Go to line start" })
map("n", "<C-2>", "<End>", { desc = "Go to line end" })

-- === Window navigation with Ctrl + Arrow Keys ===
map("n", "<C-Left>", "<C-w>h", { desc = "Move to left window" })
map("n", "<C-Down>", "<C-w>j", { desc = "Move to lower window" })
map("n", "<C-Up>", "<C-w>k", { desc = "Move to upper window" })
map("n", "<C-Right>", "<C-w>l", { desc = "Move to right window" })
