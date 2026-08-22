/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./templates/**/*.html",
    "./templates/components/**/*.html",
    "./templates/partials/**/*.html",
    "./accounts/templates/**/*.html",
    "./providers/templates/**/*.html",
    "./services/templates/**/*.html",
    "./bookings/templates/**/*.html",
    "./dashboard/templates/**/*.html",
    "./notifications/templates/**/*.html",
    "./chat/templates/**/*.html",
    "./static/js/**/*.js",
  ],
  theme: {
    extend: {},
  },
  plugins: [],
};
