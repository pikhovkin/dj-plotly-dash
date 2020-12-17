# AUTO GENERATED FILE - DO NOT EDIT

dtcStyledComponent <- function(id=NULL, style=NULL, value=NULL) {
    
    props <- list(id=id, style=style, value=value)
    if (length(props) > 0) {
        props <- props[!vapply(props, is.null, logical(1))]
    }
    component <- list(
        props = props,
        type = 'StyledComponent',
        namespace = 'dash_test_components',
        propNames = c('id', 'style', 'value'),
        package = 'dashTestComponents'
        )

    structure(component, class = c('dash_component', 'list'))
}
