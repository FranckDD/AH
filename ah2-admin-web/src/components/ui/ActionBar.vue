<template>
    <!-- Barre collante en bas ; sous md les boutons passent en pleine largeur (principal en premier) -->
    <div class="sticky bottom-0 z-10 flex flex-col-reverse gap-2 border-t border-tone-neutral-border bg-white px-4 py-3 md:flex-row md:items-center md:justify-between md:px-5">
        <div class="flex flex-col gap-2 md:flex-row [&>*]:w-full md:[&>*]:w-auto"><slot name="secondary" /></div>
        <div class="flex flex-col gap-2 md:flex-row [&>*]:w-full md:[&>*]:w-auto"><slot /></div>
    </div>
</template>
