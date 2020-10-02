
const NumbaGenerator = {
  props: ['numba', 'quote'],
  template: `
    <div class='card mb-5'>
      <div class='card-content'>
        <div class="columns">
          <div class="column is-2">
            <h3 class='is-size-1 has-text-centered'>
              <span v-if="numba">{{ numba }}</span>
            </h3>
          </div>
          <div class="column">
            <p>{{ quote ? quote.quote : '' }}</p>
            <p>{{ quote ? quote.author : '' }}</p>
          </div>
        </div>
        <p class='mt-3'><button class='button is-primary' @click="$emit('generate')">Generate Some Randomness</button></p>
      </div>
    </div>
  `
}

const NumbasList = {
  props: ['numbas'],
  template:  `
    <table class='table is-fullwidth'>
      <thead>
        <tr>
          <th>Random Number</th>
          <th>Random Quote</th>
          <th>Author</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(numba, i) in numbas" :key="numba.id">
          <td>{{ numba.value }}</td>
          <td>{{ numba.quote.quote }}</td>
          <td>{{ numba.quote.author }}</td>
        </tr>
      </tbody>
    </table>
  `
}

function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
      const cookies = document.cookie.split(';');
      for (let i = 0; i < cookies.length; i++) {
          const cookie = cookies[i].trim();
          // Does this cookie string begin with the name we want?
          if (cookie.substring(0, name.length + 1) === (name + '=')) {
              cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
              break;
          }
      }
  }
  return cookieValue;
}
const csrftoken = getCookie('csrftoken');

new Vue({
  el: '#numba-app',
  components: {
    'numba-generator': NumbaGenerator,
    'numbas-list': NumbasList
  },
  data: function() {
    return {
      currentNumba: null,
      currentQuote: null,
      numbas: []
    }
  },
  methods: {
    fetchNumbas: function() {
      const authToken = localStorage.getItem('token')
      const options = {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Token ${authToken}`
        }
      }
      fetch('/api/rando-numba/', options)
        .then(response => response.json())
        .then(numbas => {
          this.numbas = numbas
        })
        .catch(err => {
          console.error('Fetch error', err)
        })

    },
    generateNumba: function() {
      console.log('generateNumba called')
      const authToken = localStorage.getItem('token')
      const options = {
        method: 'POST',
        headers: {
          'X-CSRFToken': getCookie('csrftoken'),
          'Content-Type': 'application/json',
          'Authorization': `Token ${authToken}`
        }
      }
      fetch('/api/rando-numba/', options)
        .then(response => response.json())
        .then(randoNumba => {
          this.currentNumba = randoNumba.value
          this.currentQuote = randoNumba.quote
          let numbas = this.numbas.slice()
          numbas.unshift(randoNumba)
          this.numbas = numbas
        })
        .catch(err => {
          console.error('Fetch error', err)
        })
    }
    
  },
  beforeMount: function() {
    this.fetchNumbas()
  }
})
