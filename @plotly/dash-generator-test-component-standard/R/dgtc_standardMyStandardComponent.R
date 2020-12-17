# AUTO GENERATED FILE - DO NOT EDIT

dgtc_standardMyStandardComponent <- function(id=NULL, style=NULL, value=NULL) {
    
    props <- list(id=id, style=style, value=value)
    if (length(props) > 0) {
        props <- props[!vapply(props, is.null, logical(1))]
    }
    component <- list(
        props = props,
        type = 'MyStandardComponent',
        namespace = 'dash_generator_test_component_standard',
        propNames = c('id', 'style', 'value'),
        package = 'dashGeneratorTestComponentStandard'
        )

    structure(component, class = c('dash_component', 'list'))
}
