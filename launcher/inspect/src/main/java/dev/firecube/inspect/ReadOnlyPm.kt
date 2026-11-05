package dev.firecube.inspect

/** A deliberately query-only gateway. Mutator names are rejected before reflection. */
class ReadOnlyPm(private val service: Any) {
    private val allowed = setOf("getHomeActivities", "getPreferredActivities", "resolveIntent", "checkUidPermission")

    fun invoke(name: String, vararg args: Any?): Any? {
        require(name in allowed) { "Read-only inspector refuses $name" }
        val methods = service.javaClass.methods.filter { method ->
            method.name == name && method.parameterTypes.size == args.size &&
                method.parameterTypes.zip(args).all { (type, argument) ->
                    if (argument == null) !type.isPrimitive
                    else if (type == Integer.TYPE) argument is Int
                    else type.isInstance(argument)
                }
        }
        require(methods.size == 1) { "No unambiguous compatible $name query" }
        val method = methods.single()
        method.isAccessible = true
        return method.invoke(service, *args)
    }

    fun signatures(names: Set<String>): List<String> = service.javaClass.methods
        .filter { it.name in names }.map { method ->
            method.name + "(" + method.parameterTypes.joinToString(",") { it.name } + ")"
        }.distinct().sorted()
}
