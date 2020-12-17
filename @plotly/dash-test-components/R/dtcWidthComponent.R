# AUTO GENERATED FILE - DO NOT EDIT

dtcWidthComponent <- function(id=NULL, width=NULL) {
    
    props <- list(id=id, width=width)
    if (length(props) > 0) {
        props <- props[!vapply(props, is.null, logical(1))]
    }
    component <- list(
        props = props,
        type = 'WidthComponent',
        namespace = 'dash_test_components',
        propNames = c('id', 'width'),
        package = 'dashTestComponents'
        )

    structure(component, class = c('dash_component', 'list'))
}
