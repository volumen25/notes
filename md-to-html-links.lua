-- Lua filter to convert Markdown links to HTML anchor links
function Link(el)
    -- Check if the link URL ends with '.md'
    if el.target:match('%.md$') then
        -- Remove the date prefix (YYYY-MM-DD-) and '.md' extension from the target
        local anchor = el.target:gsub('^%d%d%d%d%-%d%d%-%d%d%-', ''):gsub('%.md$', '')
        -- Convert to lowercase and replace spaces with hyphens for the anchor
        anchor = anchor:lower():gsub('%s+', '-')
        -- Update the link target to point to the anchor in index.html
        el.target = '#' .. anchor
        -- Update the link text: remove date prefix and capitalize words
        local link_text = el.content[1].text:gsub('^%d%d%d%d%-%d%d%-%d%d%-', '')
        -- Replace hyphens with spaces and capitalize each word
        link_text = link_text:gsub('-', ' '):gsub('(%w)(%w*)', function(first, rest)
            return first:upper() .. rest:lower()
        end)
        el.content = pandoc.Str(link_text)
        return el
    end
end