# AUTO GENERATED FILE - DO NOT EDIT

dtcCollapseComponent <- function(children=NULL, display=NULL, id=NULL) {
    
    props <- list(children=children, display=display, id=id)
    if (length(props) > 0) {
        props <- props[!vapply(props, is.null, logical(1))]
    }
    component <- list(
        props = props,
        type = 'CollapseComponent',
        namespace = 'dash_test_components',
        propNames = c('children', 'display', 'id'),
        package = 'dashTestComponents'
        )

    structure(component, class = c('dash_component', 'list'))
}
