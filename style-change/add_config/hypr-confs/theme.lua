-- Read the shared Hyprlang palette without executing it as Lua.
-- colors.conf contains variables only, so hyprlock can source the same file.
local config_dir = debug.getinfo(1, "S").source:sub(2):match("(.*/)")
local file = assert(io.open(config_dir .. "colors.conf", "r"))
local variables = {}
for raw_line in file:lines() do
    local line = raw_line:gsub("#.*$", "")
    local name, value = line:match("^%s*%$([%w_]+)%s*=%s*(.-)%s*$")
    if name then variables[name] = value end
end
file:close()

local function expand(value, depth)
    assert(depth < 16, "Circular reference in colors.conf")
    return (value:gsub("%$([%w_]+)", function(name)
        return expand(assert(variables[name], "Undefined color: " .. name), depth + 1)
    end))
end

local function gradient(value)
    value = expand(value, 0)
    -- Hex values in Hyprlang use ARGB; Lua's gradient API takes color strings.
    value = value:gsub("0[xX](%x%x)(%x%x%x%x%x%x)", function(alpha, rgb)
        return "rgba(" .. rgb .. alpha .. ")"
    end)
    local angle = tonumber(value:match("([%d.]+)deg")) or 0
    local colors = {}
    for color in value:gmatch("rgba?%b()") do colors[#colors + 1] = color end
    assert(#colors > 0, "Empty border gradient in colors.conf")
    return { colors = colors, angle = angle }
end

return {
    active_border = gradient(assert(variables.hypr_active_border, "Missing hypr_active_border")),
    inactive_border = gradient(assert(variables.hypr_inactive_border, "Missing hypr_inactive_border")),
}
