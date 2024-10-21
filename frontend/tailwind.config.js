module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
    // Add any other files that contain Tailwind classes
  ],
  theme: {
    extend: {},
  },
  plugins: [
    require('@tailwindcss/line-clamp'),
    // Any other plugins you're using
  ],
}