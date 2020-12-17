# AUTO GENERATED FILE - DO NOT EDIT

dtcFragmentComponent <- function(children=NULL, id=NULL) {
    
    props <- list(children=children, id=id)
    if (length(props) > 0) {
        props <- props[!vapply(props, is.null, logical(1))]
    }
    component <- list(
        props = props,
        type = 'FragmentComponent',
        namespace = 'dash_test_components',
        propNames = c('children', 'id'),
        package = 'dashTestComponents'
        )

    structure(component, class = c('dash_component', 'list'))
}
