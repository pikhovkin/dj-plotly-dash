# AUTO GENERATED FILE - DO NOT EDIT

dtcAsyncComponent <- function(id=NULL, value=NULL) {
    
    props <- list(id=id, value=value)
    if (length(props) > 0) {
        props <- props[!vapply(props, is.null, logical(1))]
    }
    component <- list(
        props = props,
        type = 'AsyncComponent',
        namespace = 'dash_test_components',
        propNames = c('id', 'value'),
        package = 'dashTestComponents'
        )

    structure(component, class = c('dash_component', 'list'))
}
