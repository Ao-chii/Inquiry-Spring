<template>
  <v-hover>
  <template v-slot:default="{ isHovering, props }">
    <v-card
      v-bind="props"
      :color="isHovering ? 'primary' : 'grey lighten-3'"
      style="min-height: 100px; width: 300px;"
    >
      <v-card-title>Hover over me</v-card-title>
      <v-card-text>
        当前状态：{{ isHovering ? '悬停中' : '未悬停' }}
      </v-card-text>
    </v-card>
  </template>
</v-hover>
</template>