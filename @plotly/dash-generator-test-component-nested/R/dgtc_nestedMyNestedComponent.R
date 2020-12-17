# AUTO GENERATED FILE - DO NOT EDIT

dgtc_nestedMyNestedComponent <- function(id=NULL, value=NULL) {
    
    props <- list(id=id, value=value)
    if (length(props) > 0) {
        props <- props[!vapply(props, is.null, logical(1))]
    }
    component <- list(
        props = props,
        type = 'MyNestedComponent',
        namespace = 'dash_generator_test_component_nested',
        propNames = c('id', 'value'),
        package = 'dashGeneratorTestComponentNested'
        )

    structure(component, class = c('dash_component', 'list'))
}
