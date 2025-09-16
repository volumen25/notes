-- Lua filter to convert Markdown links to HTML anchor links
function Link(el)
    -- Check if the link URL ends with '.md'
    if el.target:match('%.md$') then
        -- Remove the date prefix (YYYY-MM-DD-) and '.md' extension
        local anchor = el.target:gsub('^%d%d%d%d%-%d%d%-%d%d%-', ''):gsub('%.md$', '')
        -- Convert to lowercase and replace spaces with hyphens
        anchor = anchor:lower():gsub('%s+', '-')
        -- Update the link target to point to the anchor in index.html
        el.target = '#' .. anchor
        return el
    end
end